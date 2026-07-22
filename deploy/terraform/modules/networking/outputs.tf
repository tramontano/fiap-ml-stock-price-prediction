# =============================================================================
# Módulo: Networking — Outputs
# Expõe os IDs necessários para os módulos compute, iam, etc.
# =============================================================================

output "vpc_id" {
  description = "ID da VPC criada."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs das subnets públicas (para o ALB)."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs das subnets privadas (para o ECS Fargate)."
  value       = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  description = "ID do Security Group do ALB."
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ID do Security Group do ECS."
  value       = aws_security_group.ecs.id
}
