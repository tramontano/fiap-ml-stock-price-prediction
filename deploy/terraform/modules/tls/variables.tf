# =============================================================================
# Módulo: TLS — Variáveis de Entrada
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
# Domínio e Certificado
# ==========================================
variable "domain_name" {
  description = "Domínio principal para o certificado SSL/TLS (ex: api.example.com)."
  type        = string
}

variable "subject_alternative_names" {
  description = "Lista de domínios alternativos para o certificado (ex: [\"*.example.com\", \"example.com\"])."
  type        = list(string)
  default     = []
}

variable "validation_method" {
  description = "Método de validação do certificado ACM: 'DNS' ou 'EMAIL'."
  type        = string
  default     = "DNS"
  validation {
    condition     = contains(["DNS", "EMAIL"], var.validation_method)
    error_message = "Validation method deve ser 'DNS' ou 'EMAIL'."
  }
}

# ==========================================
# ALB Configuration
# ==========================================
variable "alb_arn" {
  description = "ARN do Application Load Balancer."
  type        = string
}

variable "alb_security_group_id" {
  description = "ID do Security Group do ALB."
  type        = string
}

variable "target_group_arn" {
  description = "ARN do Target Group do ALB."
  type        = string
}

# ==========================================
# SSL/TLS Policy
# ==========================================
variable "ssl_policy" {
  description = "Política SSL/TLS do ALB (ex: 'ELBSecurityPolicy-TLS-1-2-2017-01' para compatibilidade, 'ELBSecurityPolicy-TLS-1-2-Ext-2018-06' para segurança moderna)."
  type        = string
  default     = "ELBSecurityPolicy-TLS-1-2-2017-01"
}

# ==========================================
# Tags
# ==========================================
variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
