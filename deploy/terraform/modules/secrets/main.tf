# =============================================================================
# Módulo: Secrets Manager — Gerenciamento de Credenciais Sensíveis
#
# Este módulo centraliza o armazenamento seguro de credenciais em produção:
#   • MLflow Tracking (username + password)
#   • DagsHub App Token
#   • Autenticação da API (admin username + password)
#   • Optuna Storage URI (PostgreSQL)
#
# Cada secret é armazenado como JSON no AWS Secrets Manager com rotação
# automática e auditoria via CloudTrail.
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Module      = "secrets"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Secret: MLflow Tracking Credentials
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "mlflow_credentials" {
  name                    = "${local.name_prefix}-mlflow-credentials"
  description             = "Credenciais de autenticação para MLflow Tracking Server (DagsHub)"
  recovery_window_in_days = var.recovery_window_in_days
  tags                    = merge(local.common_tags, { Name = "${local.name_prefix}-mlflow-credentials" })
}

resource "aws_secretsmanager_secret_version" "mlflow_credentials" {
  secret_id = aws_secretsmanager_secret.mlflow_credentials.id
  secret_string = jsonencode({
    username = var.mlflow_tracking_username
    password = var.mlflow_tracking_password
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Secret: DagsHub App Token
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "dagshub_token" {
  name                    = "${local.name_prefix}-dagshub-token"
  description             = "Token de aplicação do DagsHub para acesso ao MLflow"
  recovery_window_in_days = var.recovery_window_in_days
  tags                    = merge(local.common_tags, { Name = "${local.name_prefix}-dagshub-token" })
}

resource "aws_secretsmanager_secret_version" "dagshub_token" {
  secret_id     = aws_secretsmanager_secret.dagshub_token.id
  secret_string = var.dagshub_app_token
}

# ─────────────────────────────────────────────────────────────────────────────
# Secret: API Authentication (Admin Credentials)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "api_credentials" {
  name                    = "${local.name_prefix}-api-credentials"
  description             = "Credenciais de autenticação básica para rotas admin da API"
  recovery_window_in_days = var.recovery_window_in_days
  tags                    = merge(local.common_tags, { Name = "${local.name_prefix}-api-credentials" })
}

resource "aws_secretsmanager_secret_version" "api_credentials" {
  secret_id = aws_secretsmanager_secret.api_credentials.id
  secret_string = jsonencode({
    username = var.api_username
    password = var.api_password
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Secret: Optuna Storage URI (Opcional - PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "optuna_storage_uri" {
  count                   = var.optuna_storage_uri != null ? 1 : 0
  name                    = "${local.name_prefix}-optuna-storage-uri"
  description             = "URI de conexão com banco PostgreSQL para armazenamento do Optuna"
  recovery_window_in_days = var.recovery_window_in_days
  tags                    = merge(local.common_tags, { Name = "${local.name_prefix}-optuna-storage-uri" })
}

resource "aws_secretsmanager_secret_version" "optuna_storage_uri" {
  count         = var.optuna_storage_uri != null ? 1 : 0
  secret_id     = aws_secretsmanager_secret.optuna_storage_uri[0].id
  secret_string = var.optuna_storage_uri
}

# ─────────────────────────────────────────────────────────────────────────────
# Secret: MinIO Credentials (Dev Only - Não usar em Prod)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "minio_credentials" {
  count                   = var.minio_root_user != null ? 1 : 0
  name                    = "${local.name_prefix}-minio-credentials"
  description             = "Credenciais de acesso ao MinIO (apenas para dev/testes)"
  recovery_window_in_days = var.recovery_window_in_days
  tags                    = merge(local.common_tags, { Name = "${local.name_prefix}-minio-credentials" })
}

resource "aws_secretsmanager_secret_version" "minio_credentials" {
  count = var.minio_root_user != null ? 1 : 0
  secret_id = aws_secretsmanager_secret.minio_credentials[0].id
  secret_string = jsonencode({
    root_user     = var.minio_root_user
    root_password = var.minio_root_password
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Política de Rotação Automática (Opcional - Futuro)
# ─────────────────────────────────────────────────────────────────────────────
# Nota: A rotação automática requer uma Lambda function que atualize as
# credenciais no serviço remoto (ex: DagsHub). Deixado como comentário
# para implementação futura.
#
# resource "aws_secretsmanager_secret_rotation" "mlflow_credentials" {
#   secret_id           = aws_secretsmanager_secret.mlflow_credentials.id
#   rotation_rules {
#     automatically_after_days = 30
#   }
#   rotation_lambda_arn = aws_lambda_function.rotate_secrets.arn
# }
