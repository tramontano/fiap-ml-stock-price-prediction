# =============================================================================
# Módulo: ECR — Elastic Container Registry
#
# Docker Hub privado e integrado à VPC.
# O CI/CD (GitHub Actions) envia a imagem para cá; o ECS Fargate puxa daqui.
# =============================================================================

locals {
  repo_name = "${var.project_name}-${var.environment}-api"

  common_tags = merge(var.tags, {
    Module      = "ecr"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Repositório ECR — Armazena as imagens Docker da API
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "api" {
  name                 = local.repo_name
  image_tag_mutability = var.image_tag_mutability
  force_delete         = var.environment == "dev" ? true : false

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name = local.repo_name
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle Policy — Mantém apenas as N imagens mais recentes
# Evita que o repositório cresça indefinidamente e gere custos extras.
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Manter apenas as ${var.max_image_count} imagens mais recentes"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.max_image_count
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
