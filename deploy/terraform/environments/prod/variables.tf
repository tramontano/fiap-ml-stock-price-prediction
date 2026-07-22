# =============================================================================
# Ambiente PROD — Variáveis
# =============================================================================

variable "project_name" {
  description = "Nome do projeto."
  type        = string
}

variable "environment" {
  description = "Ambiente."
  type        = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "task_cpu" {
  description = "CPU do ECS Task em PROD."
  type        = number
}

variable "task_memory" {
  description = "Memória do ECS Task em PROD."
  type        = number
}

variable "min_capacity" {
  description = "Mínimo de instâncias ECS em PROD."
  type        = number
}

variable "max_capacity" {
  description = "Máximo de instâncias ECS em PROD."
  type        = number
}

variable "aws_region" {
  description = "Região da AWS."
  type        = string
  default     = "us-east-1"
}
