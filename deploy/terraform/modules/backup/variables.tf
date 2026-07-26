# =============================================================================
# Módulo: Backup & Disaster Recovery — Variáveis de Entrada
# =============================================================================

variable "project_name" {
  description = "Nome do projeto, usado como prefixo nos nomes dos recursos."
  type        = string
}

variable "environment" {
  description = "Ambiente de deploy (dev, staging, production)."
  type        = string
}

# ==========================================
# S3 Replication (Cross-Region)
# ==========================================
variable "source_bucket_id" {
  description = "ID do bucket S3 de origem (ex: models-dev)."
  type        = string
}

variable "source_bucket_arn" {
  description = "ARN do bucket S3 de origem."
  type        = string
}

variable "destination_bucket_id" {
  description = "ID do bucket S3 de destino em outra região (ex: models-dev-backup)."
  type        = string
}

variable "destination_bucket_arn" {
  description = "ARN do bucket S3 de destino."
  type        = string
}

variable "enable_replication" {
  description = "Se true, ativa replicação cross-region do S3."
  type        = bool
  default     = true
}

variable "enable_mfa_delete" {
  description = "Se true, requer MFA para deletar versões do bucket (apenas prod)."
  type        = bool
  default     = false
}

# ==========================================
# AWS Backup Configuration
# ==========================================
variable "backup_schedule" {
  description = "Agendamento de backup em formato cron (ex: 'cron(0 5 ? * * *)' para 5 AM UTC)."
  type        = string
  default     = "cron(0 5 ? * * *)"  # 5 AM UTC diariamente
}

variable "backup_retention_days" {
  description = "Dias para reter backups antes de deletar."
  type        = number
  default     = 30
}

variable "cold_storage_after_days" {
  description = "Dias antes de mover backup para cold storage (Glacier)."
  type        = number
  default     = 7
}

variable "backup_resources" {
  description = "Lista de ARNs de recursos para fazer backup (ex: RDS, DynamoDB)."
  type        = list(string)
  default     = []
}

# ==========================================
# Tags
# ==========================================
variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
