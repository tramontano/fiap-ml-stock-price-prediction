# =============================================================================
# Módulo: ECR — Outputs
# =============================================================================

output "repository_url" {
  description = "URL do repositório ECR (usado no docker push e no ECS task definition)."
  value       = aws_ecr_repository.api.repository_url
}

output "repository_arn" {
  description = "ARN do repositório ECR."
  value       = aws_ecr_repository.api.arn
}

output "repository_name" {
  description = "Nome do repositório ECR."
  value       = aws_ecr_repository.api.name
}
