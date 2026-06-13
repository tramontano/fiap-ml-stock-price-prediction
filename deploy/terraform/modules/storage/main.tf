# =============================================================================
# Módulo: Storage — S3 Buckets (Data Lake + Model Registry)
#
# Arquitetura Medallion:
#   Bronze → Dados crus do yfinance (Parquet)
#   Silver → Dados limpos (Open, High, Low, Close, Volume)
#   Gold   → Features transformadas prontas para o LSTM
#   Models → Artefatos treinados (lstm_model.keras, feature_pipeline.pkl)
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  # Definição centralizada dos buckets do Data Lake
  buckets = {
    bronze = {
      name       = "${local.name_prefix}-bronze"
      purpose    = "Dados crus do yfinance"
      versioning = false
      lifecycle  = true
    }
    silver = {
      name       = "${local.name_prefix}-silver"
      purpose    = "Dados limpos (OHLCV)"
      versioning = false
      lifecycle  = true
    }
    gold = {
      name       = "${local.name_prefix}-gold"
      purpose    = "Features transformadas para LSTM"
      versioning = false
      lifecycle  = false
    }
    models = {
      name       = "${local.name_prefix}-models"
      purpose    = "Artefatos treinados (modelo + scaler)"
      versioning = true # Permite reverter se apagar um modelo por engano
      lifecycle  = false
    }
  }

  common_tags = merge(var.tags, {
    Module      = "storage"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Buckets — Um para cada camada do Data Lake
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "datalake" {
  for_each = local.buckets

  bucket        = each.value.name
  force_destroy = var.force_destroy

  tags = merge(local.common_tags, {
    Name    = each.value.name
    Purpose = each.value.purpose
    Layer   = each.key
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Versionamento — Ativo no bucket models (segurança contra apagamento)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_versioning" "datalake" {
  for_each = {
    for k, v in local.buckets : k => v
    if v.versioning && var.enable_versioning
  }

  bucket = aws_s3_bucket.datalake[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Encriptação — SSE-S3 em todos os buckets (dados em repouso protegidos)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_server_side_encryption_configuration" "datalake" {
  for_each = local.buckets

  bucket = aws_s3_bucket.datalake[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Bloqueio de Acesso Público — Nenhum bucket deve ser público
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_public_access_block" "datalake" {
  for_each = local.buckets

  bucket = aws_s3_bucket.datalake[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle — Move dados antigos do bronze/silver para Glacier (economia)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_lifecycle_configuration" "datalake" {
  for_each = {
    for k, v in local.buckets : k => v
    if v.lifecycle
  }

  bucket = aws_s3_bucket.datalake[each.key].id

  rule {
    id     = "archive-to-glacier"
    status = "Enabled"

    transition {
      days          = var.lifecycle_glacier_days
      storage_class = "GLACIER"
    }

    # Limpa versões antigas após 180 dias (se versionamento estiver ativo)
    noncurrent_version_expiration {
      noncurrent_days = 180
    }
  }
}
