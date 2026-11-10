terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "AutoEval Sandbox"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# --- VPC & Networking ---
resource "aws_vpc" "autoeval_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "autoeval-vpc-${var.environment}"
  }
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.autoeval_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags = {
    Name = "autoeval-public-a"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.autoeval_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true
  tags = {
    Name = "autoeval-public-b"
  }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.autoeval_vpc.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}a"
  tags = {
    Name = "autoeval-private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.autoeval_vpc.id
  cidr_block        = "10.0.12.0/24"
  availability_zone = "${var.aws_region}b"
  tags = {
    Name = "autoeval-private-b"
  }
}

# Internet Gateway for Public Subnets
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.autoeval_vpc.id
  tags = {
    Name = "autoeval-igw"
  }
}

# --- Security Groups ---
resource "aws_security_group" "alb_sg" {
  name        = "autoeval-alb-sg"
  description = "Public ALB ingress"
  vpc_id      = aws_vpc.autoeval_vpc.id

  ingress {
    description = "HTTP Ingress"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "autoeval-ecs-sg"
  description = "ECS Task security group"
  vpc_id      = aws_vpc.autoeval_vpc.id

  ingress {
    description     = "Traffic from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "redis_sg" {
  name        = "autoeval-redis-sg"
  description = "ElastiCache Redis security group"
  vpc_id      = aws_vpc.autoeval_vpc.id

  ingress {
    description     = "Redis port from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }
}

# --- ElastiCache Redis Subnet Group & Cluster ---
resource "aws_elasticache_subnet_group" "redis_subnets" {
  name       = "autoeval-redis-subnets"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "autoeval-redis-${var.environment}"
  description                = "AutoEval Celery broker and result backend"
  node_type                  = "cache.t4g.micro"
  num_cache_clusters         = 2
  parameter_group_name       = "default.redis7"
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.redis_subnets.name
  security_group_ids         = [aws_security_group.redis_sg.id]
  automatic_failover_enabled = true
}

# --- ECS Cluster & CloudWatch Logs ---
resource "aws_ecs_cluster" "main" {
  name = "autoeval-cluster-${var.environment}"
}

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/autoeval-${var.environment}"
  retention_in_days = 14
}

# --- ALB & Target Group ---
resource "aws_lb" "api_alb" {
  name               = "autoeval-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

resource "aws_lb_target_group" "api_tg" {
  name        = "autoeval-tg-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.autoeval_vpc.id
  target_type = "ip"

  health_check {
    path                = "/api/v1/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_tg.arn
  }
}

# --- ECS Task Definition: FastAPI Gateway ---
resource "aws_ecs_task_definition" "api" {
  family                   = "autoeval-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.fargate_cpu)
  memory                   = tostring(var.fargate_memory)

  container_definitions = jsonencode([
    {
      name      = "autoeval-api"
      image     = var.api_container_image
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
        }
      ]
      environment = [
        { name = "APP_ENV", value = var.environment },
        { name = "REDIS_URL", value = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "api_service" {
  name            = "autoeval-api-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_groups = [aws_security_group.ecs_sg.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_tg.arn
    container_name   = "autoeval-api"
    container_port   = 8000
  }
}
