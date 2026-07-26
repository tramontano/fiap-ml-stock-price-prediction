# =============================================================================
# Módulo: IAM — Roles e Políticas (Princípio do Menor Privilégio)
#
# Duas roles distintas:
#   1. ECS Task Execution Role → Permissões para o AGENTE ECS (pull ECR, logs)
#   2. ECS Task Role            → Permissões para a APLICAÇÃO (S3, Secrets)
#
# Se a API for comprometida, o atacante só pode ler do bucket models/.
# Ele NÃO pode deletar, listar outros buckets, ou acessar IAM.
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Module      = "iam"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. ECS Task Execution Role
# Usada pelo AGENTE ECS para:
#   • Puxar imagens Docker do ECR
#   • Enviar logs para o CloudWatch
#   • Ler secrets do AWS Secrets Manager (variáveis de ambiente)
# ─────────────────────────────────────────────────────────────────────────────
data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name_prefix}-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-execution-role"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_base" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Política adicional: permite ler secrets do Secrets Manager
data "aws_iam_policy_document" "execution_secrets" {
  statement {
    sid    = "ReadSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = ["arn:aws:secretsmanager:*:*:secret:${local.name_prefix}-*"]
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  name   = "${local.name_prefix}-execution-secrets"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.execution_secrets.json
}

# Política adicional: permite ler secrets do Secrets Manager com prefixo do projeto
data "aws_iam_policy_document" "execution_secrets_manager" {
  statement {
    sid    = "ReadSecretsManager"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = ["arn:aws:secretsmanager:*:*:secret:${local.name_prefix}-*"]
  }
}

resource "aws_iam_role_policy" "execution_secrets_manager" {
  name   = "${local.name_prefix}-execution-secrets-manager"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.execution_secrets_manager.json
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. ECS Task Role
# Usada pela APLICAÇÃO (FastAPI) para:
#   • Ler modelos do S3 (s3:GetObject no bucket models/)
#   • Ler dados do Data Lake (s3:GetObject nos buckets bronze/silver/gold)
#   • Listar objetos nos buckets (s3:ListBucket)
#   • PROIBIDO: s3:DeleteObject, s3:PutObject no models/, IAM:*
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-task-role"
  })
}

# Leitura do bucket de modelos (somente GetObject — sem Delete!)
data "aws_iam_policy_document" "task_s3_models" {
  # Permissão de listar o conteúdo do bucket
  statement {
    sid    = "ListModelsBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [var.models_bucket_arn]
  }

  # Permissão de leitura dos objetos dentro do bucket
  statement {
    sid    = "ReadModelsObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]
    resources = ["${var.models_bucket_arn}/*"]
  }

  # Permissão de escrita para sincronização de modelos e ponteiros de estágio
  # Permite que a API promova modelos (Challenger -> Champion) e sincronize artefatos
  statement {
    sid    = "WriteModelsArtifacts"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:PutObjectAcl",
    ]
    resources = [
      "${var.models_bucket_arn}/runs/*",      # Artefatos de modelo (model.keras, scaler.pkl)
      "${var.models_bucket_arn}/pointers/*",  # Ponteiros de estágio (champion.json, challenger.json)
    ]
  }
}

resource "aws_iam_role_policy" "task_s3_models" {
  name   = "${local.name_prefix}-task-s3-models"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.task_s3_models.json
}

# Leitura dos buckets do Data Lake (bronze, silver, gold)
data "aws_iam_policy_document" "task_s3_datalake" {
  # ListBucket em todos os buckets
  statement {
    sid    = "ListDatalakeBuckets"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = values(var.datalake_bucket_arns)
  }

  # GetObject em todos os objetos de todos os buckets
  statement {
    sid    = "ReadDatalakeObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [for arn in values(var.datalake_bucket_arns) : "${arn}/*"]
  }

  # PutObject apenas no bronze e silver (ingestão e processamento)
  statement {
    sid    = "WriteBronzeSilver"
    effect = "Allow"
    actions = [
      "s3:PutObject",
    ]
    resources = [
      "${var.datalake_bucket_arns["bronze"]}/*",
      "${var.datalake_bucket_arns["silver"]}/*",
      "${var.datalake_bucket_arns["gold"]}/*",
    ]
  }
}

resource "aws_iam_role_policy" "task_s3_datalake" {
  name   = "${local.name_prefix}-task-s3-datalake"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.task_s3_datalake.json
}

# CloudWatch Logs — permite à aplicação emitir logs estruturados (JSON)
data "aws_iam_policy_document" "task_cloudwatch" {
  statement {
    sid    = "WriteLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "task_cloudwatch" {
  name   = "${local.name_prefix}-task-cloudwatch"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.task_cloudwatch.json
}
