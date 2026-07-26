# =============================================================================
# Módulo: Auto Scaling — Variáveis de Entrada
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
# ECS Cluster e Service
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
# Capacidade Min/Max
# ==========================================
variable "min_capacity" {
  description = "Número mínimo de tasks ECS."
  type        = number
  validation {
    condition     = var.min_capacity >= 1
    error_message = "Min capacity deve ser pelo menos 1."
  }
}

variable "max_capacity" {
  description = "Número máximo de tasks ECS."
  type        = number
  validation {
    condition     = var.max_capacity >= var.min_capacity
    error_message = "Max capacity deve ser >= min_capacity."
  }
}

# ==========================================
# CPU Scaling
# ==========================================
variable "cpu_target_utilization" {
  description = "Percentual alvo de utilização de CPU para auto scaling."
  type        = number
  default     = 70
  validation {
    condition     = var.cpu_target_utilization > 0 && var.cpu_target_utilization <= 100
    error_message = "CPU target deve estar entre 1 e 100."
  }
}

# ==========================================
# Memory Scaling (Opcional)
# ==========================================
variable "enable_memory_scaling" {
  description = "Se true, ativa auto scaling baseado em memória."
  type        = bool
  default     = false
}

variable "memory_target_utilization" {
  description = "Percentual alvo de utilização de memória para auto scaling."
  type        = number
  default     = 75
  validation {
    condition     = var.memory_target_utilization > 0 && var.memory_target_utilization <= 100
    error_message = "Memory target deve estar entre 1 e 100."
  }
}

# ==========================================
# ALB Request Count Scaling (Opcional)
# ==========================================
variable "enable_alb_request_scaling" {
  description = "Se true, ativa auto scaling baseado em requisições por target."
  type        = bool
  default     = false
}

variable "alb_request_count_target" {
  description = "Número alvo de requisições por target para auto scaling."
  type        = number
  default     = 1000
}

variable "alb_resource_label" {
  description = "Resource label do ALB e Target Group (ex: app/my-alb/.../targetgroup/...)."
  type        = string
  default     = ""
}

# ==========================================
# Custom Metric Scaling (Opcional)
# ==========================================
variable "enable_custom_metric_scaling" {
  description = "Se true, ativa auto scaling baseado em métrica customizada do CloudWatch."
  type        = bool
  default     = false
}

variable "custom_metric_name" {
  description = "Nome da métrica customizada no CloudWatch."
  type        = string
  default     = ""
}

variable "custom_metric_namespace" {
  description = "Namespace da métrica customizada (ex: 'MLOps/API')."
  type        = string
  default     = ""
}

variable "custom_metric_statistic" {
  description = "Estatística da métrica (Average, Sum, Maximum, Minimum)."
  type        = string
  default     = "Average"
}

variable "custom_metric_unit" {
  description = "Unidade da métrica (Count, Seconds, Percent, etc)."
  type        = string
  default     = "Count"
}

variable "custom_metric_target_value" {
  description = "Valor alvo para a métrica customizada."
  type        = number
  default     = 100
}

# ==========================================
# Cooldown Periods
# ==========================================
variable "scale_out_cooldown" {
  description = "Segundos de espera após scale out antes de escalar novamente."
  type        = number
  default     = 60
}

variable "scale_in_cooldown" {
  description = "Segundos de espera após scale in antes de escalar novamente."
  type        = number
  default     = 300
}

# ==========================================
# Step Scaling (Picos Extremos)
# ==========================================
variable "enable_step_scaling" {
  description = "Se true, ativa step scaling para picos extremos de CPU."
  type        = bool
  default     = false
}

variable "step_scaling_cpu_threshold" {
  description = "Percentual de CPU que dispara step scaling (ex: 90)."
  type        = number
  default     = 90
  validation {
    condition     = var.step_scaling_cpu_threshold > 0 && var.step_scaling_cpu_threshold <= 100
    error_message = "Step scaling CPU threshold deve estar entre 1 e 100."
  }
}

variable "step_scaling_cooldown" {
  description = "Segundos de cooldown para step scaling."
  type        = number
  default     = 120
}

# ==========================================
# Tags
# ==========================================
variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
