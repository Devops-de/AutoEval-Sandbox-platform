output "alb_dns_name" {
  description = "Public Application Load Balancer endpoint URL"
  value       = aws_lb.api_alb.dns_name
}

output "ecs_cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.main.name
}

output "redis_primary_endpoint" {
  description = "AWS ElastiCache Redis primary endpoint address"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group for container logs"
  value       = aws_cloudwatch_log_group.ecs_logs.name
}
