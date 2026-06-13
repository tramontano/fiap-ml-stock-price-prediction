# =============================================================================
# Módulo: Storage — Variáveis de Entrada
# =============================================================================

variable "project_name" {
  description = "Nome do projeto, usado como prefixo nos nomes dos buckets."
  type        = string
}

variable "environment" {
  description = "Ambiente de deploy (dev, staging, production)."
  type        = string
}

variable "force_destroy" {
  description = "Se true, permite destruir buckets com objetos dentro (usar apenas em dev)."
  type        = bool
  default     = false
}

variable "enable_versioning" {
  description = "Ativa versionamento nos buckets (recomendado para models/)."
  type        = bool
  default     = true
}

variable "lifecycle_glacier_days" {
  description = "Dias após os quais objetos no bucket bronze são movidos para Glacier."
  type        = number
  default     = 90
}

variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
