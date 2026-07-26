# =============================================================================
# Módulo: Secrets Manager — Outputs
# =============================================================================

output "mlflow_credentials_secret_arn" {
  description = "ARN do secret com credenciais do MLflow."
  value       = aws_secretsmanager_secret.mlflow_credentials.arn
}

output "mlflow_credentials_secret_name" {
  description = "Nome do secret com credenciais do MLflow."
  value       = aws_secretsmanager_secret.mlflow_credentials.name
}

output "dagshub_token_secret_arn" {
  description = "ARN do secret com token do DagsHub."
  value       = aws_secretsmanager_secret.dagshub_token.arn
}

output "dagshub_token_secret_name" {
  description = "Nome do secret com token do DagsHub."
  value       = aws_secretsmanager_secret.dagshub_token.name
}

output "api_credentials_secret_arn" {
  description = "ARN do secret com credenciais da API."
  value       = aws_secretsmanager_secret.api_credentials.arn
}

output "api_credentials_secret_name" {
  description = "Nome do secret com credenciais da API."
  value       = aws_secretsmanager_secret.api_credentials.name
}

output "optuna_storage_uri_secret_arn" {
  description = "ARN do secret com URI do Optuna (se criado)."
  value       = try(aws_secretsmanager_secret.optuna_storage_uri[0].arn, null)
}

output "optuna_storage_uri_secret_name" {
  description = "Nome do secret com URI do Optuna (se criado)."
  value       = try(aws_secretsmanager_secret.optuna_storage_uri[0].name, null)
}

output "minio_credentials_secret_arn" {
  description = "ARN do secret com credenciais do MinIO (se criado)."
  value       = try(aws_secretsmanager_secret.minio_credentials[0].arn, null)
}

output "minio_credentials_secret_name" {
  description = "Nome do secret com credenciais do MinIO (se criado)."
  value       = try(aws_secretsmanager_secret.minio_credentials[0].name, null)
}

# ─────────────────────────────────────────────────────────────────────────────
# Outputs para uso em task definition (ECS)
# ─────────────────────────────────────────────────────────────────────────────

output "secrets_for_ecs" {
  description = "Mapa de secrets formatado para injeção na task definition do ECS."
  value = {
    MLFLOW_TRACKING_USERNAME = {
      secret_name = aws_secretsmanager_secret.mlflow_credentials.name
      secret_key  = "username"
    }
    MLFLOW_TRACKING_PASSWORD = {
      secret_name = aws_secretsmanager_secret.mlflow_credentials.name
      secret_key  = "password"
    }
    DAGSHUB_APP_TOKEN = {
      secret_name = aws_secretsmanager_secret.dagshub_token.name
      secret_key  = "DAGSHUB_APP_TOKEN"
    }
    API_USERNAME = {
      secret_name = aws_secretsmanager_secret.api_credentials.name
      secret_key  = "username"
    }
    API_PASSWORD = {
      secret_name = aws_secretsmanager_secret.api_credentials.name
      secret_key  = "password"
    }
  }
}
