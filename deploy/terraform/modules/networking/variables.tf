# =============================================================================
# Módulo: Networking — Variáveis de Entrada
# =============================================================================

variable "project_name" {
  description = "Nome do projeto, usado como prefixo em todos os recursos."
  type        = string
}

variable "environment" {
  description = "Ambiente de deploy (dev, staging, production)."
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "O ambiente deve ser 'dev', 'staging' ou 'production'."
  }
}

variable "vpc_cidr" {
  description = "Bloco CIDR da VPC principal."
  type        = string
  default     = "10.0.0.0/16"
}

variable "azs" {
  description = "Lista de Availability Zones para distribuir os recursos."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDRs das subnets públicas (Load Balancer)."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDRs das subnets privadas (ECS Fargate, banco de dados)."
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "nat_gateway_per_az" {
  description = "Se true, cria um NAT Gateway por Availability Zone (prod). Se false, cria apenas um (dev)."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
