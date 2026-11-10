variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "CIDR block for AutoEval VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "api_container_image" {
  description = "ECR Docker image URI for FastAPI Gateway"
  type        = string
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/autoeval-api:latest"
}

variable "worker_container_image" {
  description = "ECR Docker image URI for Celery Worker"
  type        = string
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/autoeval-worker:latest"
}

variable "fargate_cpu" {
  description = "Fargate CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "fargate_memory" {
  description = "Fargate Memory in MB"
  type        = number
  default     = 2048
}

variable "api_desired_count" {
  description = "Number of API Gateway Fargate tasks"
  type        = number
  default     = 2
}

variable "worker_desired_count" {
  description = "Number of Celery Worker Fargate tasks"
  type        = number
  default     = 4
}
