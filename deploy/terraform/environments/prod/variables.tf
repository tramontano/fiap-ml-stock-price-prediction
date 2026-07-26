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

# ==========================================
# Variáveis de MLOps (MLflow, DagsHub, Optuna)
# ==========================================
variable "mlflow_tracking_uri" {
  description = "URI do MLflow Tracking Server (ex: https://dagshub.com/.../mlflow)."
  type        = string
  default     = ""
}

variable "mlflow_tracking_username" {
  description = "Nome de usuário para autenticação no MLflow."
  type        = string
  default     = ""
  sensitive   = true
}

variable "mlflow_experiment_name" {
  description = "Nome do experimento no MLflow."
  type        = string
  default     = ""
}

variable "mlflow_experiment_id" {
  description = "ID do experimento no MLflow."
  type        = string
  default     = ""
}

variable "dagshub_repo_name" {
  description = "Nome do repositório no DagsHub."
  type        = string
  default     = ""
}

# ==========================================
# Variáveis de Autenticação da API
# ==========================================
variable "api_username" {
  description = "Nome de usuário para autenticação das rotas admin da API."
  type        = string
  default     = ""
  sensitive   = true
}

variable "api_password" {
  description = "Senha para autenticação das rotas admin da API."
  type        = string
  default     = ""
  sensitive   = true
}

variable "allowed_origins" {
  description = "Origens permitidas para CORS (em prod, deve ser o domínio real)."
  type        = string
  default     = "https://example.com"
}

# ==========================================
# Variáveis Opcionais (Optuna)
# ==========================================
variable "optuna_storage_uri" {
  description = "URI de armazenamento do Optuna (ex: postgresql://...). Se não fornecido, usa SQLite local."
  type        = string
  default     = null
  sensitive   = true
}

variable "container_image_tag" {
  description = "Tag da imagem Docker (ex: 'v1.0.0' em prod, deve ser versionamento semántico)."
  type        = string
  default     = "v1.0.0"
}

# ==========================================
# Variáveis de Domínio e TLS
# ==========================================
variable "domain_name" {
  description = "Domínio principal para o certificado SSL/TLS (ex: api.example.com)."
  type        = string
  default     = "api.example.com"
}

variable "subject_alternative_names" {
  description = "Lista de domínios alternativos para o certificado (ex: [\"*.example.com\", \"example.com\"])."
  type        = list(string)
  default     = []
}

# ==========================================
# Variáveis de Notificação (SNS)
# ==========================================
variable "sns_topic_arn" {
  description = "ARN do tópico SNS para notificações de alarmes (opcional)."
  type        = string
  default     = null
}
