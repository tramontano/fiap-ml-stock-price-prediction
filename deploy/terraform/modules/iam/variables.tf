# =============================================================================
# Módulo: IAM — Variáveis de Entrada
# =============================================================================

variable "project_name" {
  description = "Nome do projeto, usado como prefixo nos nomes dos recursos IAM."
  type        = string
}

variable "environment" {
  description = "Ambiente de deploy (dev, staging, production)."
  type        = string
}

variable "models_bucket_arn" {
  description = "ARN do bucket S3 de modelos (para definir políticas de acesso)."
  type        = string
}

variable "datalake_bucket_arns" {
  description = "Map de ARNs dos buckets do Data Lake (bronze, silver, gold, models)."
  type        = map(string)
}

variable "ecr_repository_arn" {
  description = "ARN do repositório ECR (para permitir pull de imagens)."
  type        = string
}

variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
