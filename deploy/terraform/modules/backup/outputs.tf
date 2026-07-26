# =============================================================================
# Módulo: Backup & Disaster Recovery — Outputs
# =============================================================================

output "backup_vault_arn" {
  description = "ARN do AWS Backup Vault."
  value       = aws_backup_vault.main.arn
}

output "backup_vault_name" {
  description = "Nome do AWS Backup Vault."
  value       = aws_backup_vault.main.name
}

output "backup_plan_id" {
  description = "ID do AWS Backup Plan."
  value       = aws_backup_plan.main.id
}

output "backup_plan_arn" {
  description = "ARN do AWS Backup Plan."
  value       = aws_backup_plan.main.arn
}

output "s3_replication_role_arn" {
  description = "ARN da IAM Role para S3 Replication."
  value       = aws_iam_role.s3_replication.arn
}

output "backup_service_role_arn" {
  description = "ARN da IAM Role para AWS Backup Service."
  value       = aws_iam_role.backup_service.arn
}

output "replication_configuration" {
  description = "Detalhes da configuração de replicação S3."
  value = {
    source_bucket      = var.source_bucket_id
    destination_bucket = var.destination_bucket_id
    enabled            = var.enable_replication
    mfa_delete         = var.enable_mfa_delete
  }
}

output "backup_configuration" {
  description = "Detalhes da configuração de backup."
  value = {
    schedule              = var.backup_schedule
    retention_days        = var.backup_retention_days
    cold_storage_days     = var.cold_storage_after_days
    backup_resources_count = length(var.backup_resources)
  }
}
