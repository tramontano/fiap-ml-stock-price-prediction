# =============================================================================
# Módulo: Storage — Outputs
# =============================================================================

output "bucket_arns" {
  description = "Map de ARNs dos buckets criados (bronze, silver, gold, models)."
  value       = { for k, v in aws_s3_bucket.datalake : k => v.arn }
}

output "bucket_names" {
  description = "Map de nomes dos buckets criados."
  value       = { for k, v in aws_s3_bucket.datalake : k => v.id }
}

output "models_bucket_arn" {
  description = "ARN do bucket de modelos (usado nas policies do IAM)."
  value       = aws_s3_bucket.datalake["models"].arn
}

output "models_bucket_name" {
  description = "Nome do bucket de modelos."
  value       = aws_s3_bucket.datalake["models"].id
}
