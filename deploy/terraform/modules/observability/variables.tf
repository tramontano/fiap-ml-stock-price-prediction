# =============================================================================
# Módulo: Observability — Variáveis de Entrada
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
# CloudWatch Logs
# ==========================================
variable "log_retention_days" {
  description = "Dias de retenção dos logs no CloudWatch (0 = indefinido, 1-3653 = dias específicos)."
  type        = number
  default     = 30
  validation {
    condition     = var.log_retention_days == 0 || (var.log_retention_days >= 1 && var.log_retention_days <= 3653)
    error_message = "Log retention deve ser 0 ou entre 1 e 3653 dias."
  }
}

# ==========================================
# CloudWatch Alarms — Thresholds
# ==========================================
variable "alarm_5xx_threshold" {
  description = "Número máximo de erros 5xx em 5 minutos antes de disparar alarme."
  type        = number
  default     = 10
}

variable "alarm_latency_threshold" {
  description = "Latência máxima em milissegundos antes de disparar alarme."
  type        = number
  default     = 1000
}

variable "alarm_ecs_cpu_threshold" {
  description = "Percentual máximo de CPU do ECS antes de disparar alarme."
  type        = number
  default     = 80
  validation {
    condition     = var.alarm_ecs_cpu_threshold > 0 && var.alarm_ecs_cpu_threshold <= 100
    error_message = "CPU threshold deve estar entre 1 e 100."
  }
}

variable "alarm_ecs_memory_threshold" {
  description = "Percentual máximo de memória do ECS antes de disparar alarme."
  type        = number
  default     = 80
  validation {
    condition     = var.alarm_ecs_memory_threshold > 0 && var.alarm_ecs_memory_threshold <= 100
    error_message = "Memory threshold deve estar entre 1 e 100."
  }
}

# ==========================================
# CloudWatch Alarms — Notificações
# ==========================================
variable "sns_topic_arn" {
  description = "ARN do tópico SNS para notificações de alarmes (opcional)."
  type        = string
  default     = null
}

# ==========================================
# ALB Metrics
# ==========================================
variable "alb_arn_suffix" {
  description = "ARN suffix do Application Load Balancer (ex: app/my-alb/1234567890abcdef)."
  type        = string
}

variable "target_group_arn_suffix" {
  description = "ARN suffix do Target Group (ex: targetgroup/my-targets/1234567890abcdef)."
  type        = string
}

# ==========================================
# ECS Metrics
# ==========================================
variable "ecs_cluster_name" {
  description = "Nome do cluster ECS."
  type        = string
}

variable "ecs_service_name" {
  description = "Nome do serviço ECS."
  type        = string
}

# ==========================================
# Tags
# ==========================================
variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
