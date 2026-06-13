# =============================================================================
# Ambiente DEV — Orquestração de Módulos
# Aqui instanciamos as peças da fábrica e construímos o ambiente.
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
  force_destroy          = true # Apenas em dev para facilitar limpezas
  enable_versioning      = true
  lifecycle_glacier_days = 30   # Em dev, envia para glacier mais rápido
}

module "ecr" {
  source = "../../modules/ecr"

  project_name         = var.project_name
  environment          = var.environment
  image_tag_mutability = "MUTABLE" # Facilita overwrites com tag 'latest' em dev
  scan_on_push         = true
  max_image_count      = 5         # Economiza espaço em dev
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
  
  container_image        = "${module.ecr.repository_url}:latest"
  task_cpu               = var.task_cpu
  task_memory            = var.task_memory
  min_capacity           = var.min_capacity
  max_capacity           = var.max_capacity

  api_env_vars = {
    "ENVIRONMENT" : var.environment,
    "S3_ENDPOINT_URL" : "",  # Na AWS real, deixamos vazio
    "ALLOWED_ORIGINS" : "*"  # Em dev, mais flexível
  }
}
