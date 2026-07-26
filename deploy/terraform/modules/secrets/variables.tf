# =============================================================================
# Módulo: Secrets Manager — Variáveis de Entrada
# =============================================================================

variable "project_name" {
  description = "Nome do projeto, usado como prefixo nos nomes dos secrets."
  type        = string
}

variable "environment" {
  description = "Ambiente de deploy (dev, staging, production)."
  type        = string
}

# ==========================================
# MLflow Credentials
# ==========================================
variable "mlflow_tracking_username" {
  description = "Nome de usuário para autenticação no MLflow Tracking Server."
  type        = string
  sensitive   = true
}

variable "mlflow_tracking_password" {
  description = "Senha/token para autenticação no MLflow Tracking Server."
  type        = string
  sensitive   = true
}

# ==========================================
# DagsHub Token
# ==========================================
variable "dagshub_app_token" {
  description = "Token de aplicação do DagsHub para acesso ao MLflow."
  type        = string
  sensitive   = true
}

# ==========================================
# API Authentication
# ==========================================
variable "api_username" {
  description = "Nome de usuário para autenticação básica das rotas admin da API."
  type        = string
  sensitive   = true
}

variable "api_password" {
  description = "Senha para autenticação básica das rotas admin da API."
  type        = string
  sensitive   = true
}

# ==========================================
# Optuna Storage (Opcional)
# ==========================================
variable "optuna_storage_uri" {
  description = "URI de conexão com banco PostgreSQL para armazenamento do Optuna (ex: postgresql://user:pass@host:5432/db). Se null, não cria secret."
  type        = string
  default     = null
  sensitive   = true
}

# ==========================================
# MinIO Credentials (Dev Only)
# ==========================================
variable "minio_root_user" {
  description = "Usuário root do MinIO (apenas para dev/testes). Se null, não cria secret."
  type        = string
  default     = null
  sensitive   = true
}

variable "minio_root_password" {
  description = "Senha root do MinIO (apenas para dev/testes). Se null, não cria secret."
  type        = string
  default     = null
  sensitive   = true
}

# ==========================================
# Configurações de Rotação
# ==========================================
variable "recovery_window_in_days" {
  description = "Janela de recuperação em dias antes de deletar um secret (7-30 dias)."
  type        = number
  default     = 7
  validation {
    condition     = var.recovery_window_in_days >= 7 && var.recovery_window_in_days <= 30
    error_message = "Recovery window deve estar entre 7 e 30 dias."
  }
}

# ==========================================
# Tags
# ==========================================
variable "tags" {
  description = "Tags adicionais para todos os recursos do módulo."
  type        = map(string)
  default     = {}
}
