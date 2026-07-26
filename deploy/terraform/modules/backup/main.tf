# =============================================================================
# Módulo: Backup & Disaster Recovery — S3 Replication, Snapshots, Backups
#
# Este módulo configura:
#   • S3 Cross-Region Replication (CRR) para Data Lake e Models
#   • Versionamento e MFA Delete para proteção
#   • Lifecycle policies para retenção de backups
#   • AWS Backup para snapshots de dados críticos
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Module      = "backup"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Replication Role — Permissão para replicar entre regiões
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_iam_role" "s3_replication" {
  name = "${local.name_prefix}-s3-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-s3-replication-role"
  })
}

resource "aws_iam_role_policy" "s3_replication" {
  name = "${local.name_prefix}-s3-replication-policy"
  role = aws_iam_role.s3_replication.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Resource = var.source_bucket_arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl"
        ]
        Resource = "${var.source_bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Resource = "${var.destination_bucket_arn}/*"
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Replication Configuration (Source Bucket)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_replication_configuration" "main" {
  depends_on = [aws_s3_bucket_versioning.source]

  role   = aws_iam_role.s3_replication.arn
  bucket = var.source_bucket_id

  rule {
    id       = "${local.name_prefix}-replication-rule"
    status   = var.enable_replication ? "Enabled" : "Disabled"
    priority = 1

    filter {
      prefix = ""  # Replicar todos os objetos
    }

    destination {
      bucket       = var.destination_bucket_arn
      storage_class = "STANDARD_IA"  # Reduzir custos no backup

      replication_time {
        status = "Enabled"
        time {
          minutes = 15  # RTC: Replication Time Control
        }
      }

      metrics {
        status = "Enabled"
        event_threshold {
          minutes = 15
        }
      }

      delete_marker_replication {
        status = "Enabled"
      }
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Versioning (Source Bucket)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_versioning" "source" {
  bucket = var.source_bucket_id

  versioning_configuration {
    status     = "Enabled"
    mfa_delete = var.enable_mfa_delete ? "Enabled" : "Disabled"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Versioning (Destination Bucket)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_versioning" "destination" {
  bucket = var.destination_bucket_id

  versioning_configuration {
    status = "Enabled"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Lifecycle Policy (Destination Bucket) — Arquivar antigos
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_lifecycle_configuration" "destination" {
  bucket = var.destination_bucket_id

  rule {
    id     = "${local.name_prefix}-archive-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365  # Deletar após 1 ano
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# AWS Backup Vault — Armazenar backups criptografados
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_backup_vault" "main" {
  name = "${local.name_prefix}-backup-vault"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backup-vault"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# AWS Backup Plan — Agendamento de backups
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_backup_plan" "main" {
  name = "${local.name_prefix}-backup-plan"

  rule {
    rule_name         = "${local.name_prefix}-daily-backup"
    target_backup_vault_name = aws_backup_vault.main.name
    schedule          = var.backup_schedule  # ex: "cron(0 5 ? * * *)" para 5 AM UTC

    lifecycle {
      cold_storage_after = var.cold_storage_after_days
      delete_after       = var.backup_retention_days
    }

    recovery_point_tags = merge(local.common_tags, {
      Name = "${local.name_prefix}-recovery-point"
    })
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backup-plan"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# AWS Backup Selection — Recursos a fazer backup
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_backup_selection" "main" {
  name            = "${local.name_prefix}-backup-selection"
  plan_id         = aws_backup_plan.main.id
  iam_role_arn    = aws_iam_role.backup_service.arn
  resources       = var.backup_resources

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backup-selection"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# IAM Role para AWS Backup Service
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_iam_role" "backup_service" {
  name = "${local.name_prefix}-backup-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backup-service-role"
  })
}

resource "aws_iam_role_policy_attachment" "backup_service" {
  role       = aws_iam_role.backup_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

# ─────────────────────────────────────────────────────────────────────────────
# Data Source — Informações da Conta AWS
# ─────────────────────────────────────────────────────────────────────────────
data "aws_caller_identity" "current" {}
