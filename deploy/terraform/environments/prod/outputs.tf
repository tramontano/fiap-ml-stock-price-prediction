# =============================================================================
# Ambiente PROD — Outputs
# =============================================================================

output "api_url" {
  description = "URL público do Load Balancer de Produção."
  value       = "http://${module.compute.alb_dns_name}"
}

output "ecr_repository_url" {
  description = "URL do repositório ECR de Produção (usado no Github Actions)."
  value       = module.ecr.repository_url
}

output "models_bucket_name" {
  description = "Nome do bucket S3 onde os artefatos Champion de ML devem ser promovidos."
  value       = module.storage.models_bucket_name
}
