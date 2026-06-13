# =============================================================================
# Módulo: Compute — Variáveis de Entrada
# =============================================================================

variable "project_name" {
  description = "Nome do projeto."
  type        = string
}

variable "environment" {
  description = "Ambiente de deploy."
  type        = string
}

variable "vpc_id" {
  description = "ID da VPC."
  type        = string
}

variable "public_subnet_ids" {
  description = "IDs das subnets públicas (para o ALB)."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "IDs das subnets privadas (para o ECS Service)."
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security Group ID para o ALB."
  type        = string
}

variable "ecs_security_group_id" {
  description = "Security Group ID para o ECS Fargate."
  type        = string
}

variable "ecs_execution_role_arn" {
  description = "ARN da role de execução do ECS."
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ARN da role da task do ECS."
  type        = string
}

variable "container_image" {
  description = "URL da imagem Docker a ser usada (do ECR)."
  type        = string
}

variable "container_port" {
  description = "Porta onde a API expõe o serviço."
  type        = number
  default     = 8000
}

variable "task_cpu" {
  description = "CPU alocada para a task Fargate (em unidades, ex: 256, 512, 1024)."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Memória alocada para a task Fargate (em MB, ex: 1024, 2048)."
  type        = number
  default     = 1024
}

variable "min_capacity" {
  description = "Número mínimo de containers rodando."
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Número máximo de containers rodando (Auto Scaling)."
  type        = number
  default     = 3
}

variable "api_env_vars" {
  description = "Variáveis de ambiente adicionais para o container."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags adicionais."
  type        = map(string)
  default     = {}
}
