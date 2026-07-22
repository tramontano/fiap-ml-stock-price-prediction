# =============================================================================
# Módulo: Compute — Outputs
# =============================================================================

output "alb_dns_name" {
  description = "URL do Load Balancer para acessar a API."
  value       = aws_lb.api.dns_name
}

output "ecs_cluster_name" {
  description = "Nome do ECS Cluster."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Nome do ECS Service."
  value       = aws_ecs_service.api.name
}
