# =============================================================================
# Módulo: ECR — Variáveis de Entrada
# =============================================================================

variable "project_name" {
  description = "Nome do projeto, usado como prefixo no repositório."
  type        = string
}

variable "environment" {
  description = "Ambiente de deploy (dev, staging, production)."
  type        = string
}

variable "image_tag_mutability" {
  description = "Mutabilidade das tags das imagens (MUTABLE ou IMMUTABLE)."
  type        = string
  default     = "IMMUTABLE"
}

variable "scan_on_push" {
  description = "Ativa scan de vulnerabilidades (CVEs) ao enviar uma imagem."
  type        = bool
  default     = true
}

variable "max_image_count" {
  description = "Número máximo de imagens a manter no repositório (as mais antigas são eliminadas)."
  type        = number
  default     = 10
}

variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
