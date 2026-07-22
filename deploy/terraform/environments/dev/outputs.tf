# =============================================================================
# Ambiente DEV — Outputs
# =============================================================================

output "api_url" {
  description = "URL público do Load Balancer (para testes e requisições HTTP)."
  value       = "http://${module.compute.alb_dns_name}"
}

output "ecr_repository_url" {
  description = "URL do repositório ECR (usado no Github Actions)."
  value       = module.ecr.repository_url
}

output "models_bucket_name" {
  description = "Nome do bucket S3 onde os artefatos do MLflow devem ser salvos."
  value       = module.storage.models_bucket_name
}
