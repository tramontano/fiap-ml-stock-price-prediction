# =============================================================================
# Ambiente PROD — Orquestração de Módulos
# Produção prioriza segurança, imutabilidade e alta disponibilidade.
# =============================================================================

module "networking" {
  source = "../../modules/networking"

  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  azs                  = ["${var.aws_region}a", "${var.aws_region}b"]
  public_subnet_cidrs  = [cidrsubnet(var.vpc_cidr, 8, 1), cidrsubnet(var.vpc_cidr, 8, 2)]
  private_subnet_cidrs = [cidrsubnet(var.vpc_cidr, 8, 101), cidrsubnet(var.vpc_cidr, 8, 102)]
}

module "storage" {
  source = "../../modules/storage"

  project_name           = var.project_name
  environment            = var.environment
  force_destroy          = false # Nunca permitir deleção de buckets não vazios em prod
  enable_versioning      = true  # Fundamental para fallback de modelos
  lifecycle_glacier_days = 90    # Retém em standard por mais tempo
}

module "ecr" {
  source = "../../modules/ecr"

  project_name         = var.project_name
  environment          = var.environment
  image_tag_mutability = "IMMUTABLE" # Evita sobrescrita de tags (exigindo versionamento semântico como v1.0.0)
  scan_on_push         = true
  max_image_count      = 30          # Mantém histórico maior de versões
}

module "iam" {
  source = "../../modules/iam"

  project_name         = var.project_name
  environment          = var.environment
  models_bucket_arn    = module.storage.models_bucket_arn
  datalake_bucket_arns = module.storage.bucket_arns
  ecr_repository_arn   = module.ecr.repository_arn
}

module "compute" {
  source = "../../modules/compute"

  project_name           = var.project_name
  environment            = var.environment
  vpc_id                 = module.networking.vpc_id
  public_subnet_ids      = module.networking.public_subnet_ids
  private_subnet_ids     = module.networking.private_subnet_ids
  alb_security_group_id  = module.networking.alb_security_group_id
  ecs_security_group_id  = module.networking.ecs_security_group_id
  ecs_execution_role_arn = module.iam.ecs_execution_role_arn
  ecs_task_role_arn      = module.iam.ecs_task_role_arn
  
  container_image        = "${module.ecr.repository_url}:latest" # No fluxo CI/CD, isso será sobrescrito pelo ID exato da imagem
  task_cpu               = var.task_cpu
  task_memory            = var.task_memory
  min_capacity           = var.min_capacity
  max_capacity           = var.max_capacity

  api_env_vars = {
    "ENVIRONMENT" : var.environment,
    "S3_ENDPOINT_URL" : "",
    "ALLOWED_ORIGINS" : "https://meu-front-end-ficticio.com" # Em prod, deve ser o domínio real da aplicação
  }
}
