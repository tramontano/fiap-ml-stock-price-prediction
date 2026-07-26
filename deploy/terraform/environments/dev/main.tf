# =============================================================================
# Ambiente DEV — Orquestração de Módulos
# Aqui instanciamos as peças da fábrica e construímos o ambiente.
# =============================================================================

module "networking" {
  source = "../../modules/networking"

  project_name           = var.project_name
  environment            = var.environment
  vpc_cidr               = var.vpc_cidr
  azs                    = ["${var.aws_region}a", "${var.aws_region}b"]
  public_subnet_cidrs    = [cidrsubnet(var.vpc_cidr, 8, 1), cidrsubnet(var.vpc_cidr, 8, 2)]
  private_subnet_cidrs   = [cidrsubnet(var.vpc_cidr, 8, 101), cidrsubnet(var.vpc_cidr, 8, 102)]
  nat_gateway_per_az     = false  # Dev: um único NAT Gateway para reduzir custos
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
  
  container_image        = "${module.ecr.repository_url}:${var.container_image_tag}"
  container_port         = 8001  # Compatibilidade com docker-compose.yml
  container_image_tag    = var.container_image_tag
  task_cpu               = var.task_cpu
  task_memory            = var.task_memory
  min_capacity           = var.min_capacity
  max_capacity           = var.max_capacity

  # Variáveis de ambiente simples (não-sensíveis)
  api_env_vars = {
    "ENVIRONMENT"              = var.environment
    "S3_ENDPOINT_URL"          = ""  # Na AWS real, deixamos vazio
    "ALLOWED_ORIGINS"          = "*" # Em dev, mais flexível
    "MLFLOW_TRACKING_URI"      = var.mlflow_tracking_uri
    "MLFLOW_TRACKING_USERNAME" = var.mlflow_tracking_username
    "MLFLOW_EXPERIMENT_NAME"   = var.mlflow_experiment_name
    "MLFLOW_EXPERIMENT_ID"     = var.mlflow_experiment_id
    "DAGSHUB_REPO_NAME"        = var.dagshub_repo_name
    "API_USERNAME"             = var.api_username
    "API_PASSWORD"             = var.api_password
    "OPTUNA_STORAGE_URI"       = var.optuna_storage_uri != null ? var.optuna_storage_uri : ""
  }

  # Em dev, usar variáveis de ambiente simples; em prod, usar Secrets Manager
  api_secrets = {}
}

module "autoscaling" {
  source = "../../modules/autoscaling"

  project_name                = var.project_name
  environment                 = var.environment
  ecs_cluster_name            = module.compute.ecs_cluster_name
  ecs_service_name            = module.compute.ecs_service_name
  min_capacity                = var.min_capacity
  max_capacity                = var.max_capacity
  cpu_target_utilization      = 70
  enable_memory_scaling       = false  # Em dev, apenas CPU
  enable_alb_request_scaling  = false
  enable_custom_metric_scaling = false
  enable_step_scaling         = false
}

module "observability" {
  source = "../../modules/observability"

  project_name              = var.project_name
  environment               = var.environment
  log_retention_days        = 7   # Em dev, retenção mais curta
  alarm_5xx_threshold       = 20  # Mais tolerante em dev
  alarm_latency_threshold   = 2000
  alarm_ecs_cpu_threshold   = 85
  alarm_ecs_memory_threshold = 85
  sns_topic_arn             = null  # Sem notificações em dev
  alb_arn_suffix            = module.compute.alb_arn_suffix
  target_group_arn_suffix   = module.compute.target_group_arn_suffix
  ecs_cluster_name          = module.compute.ecs_cluster_name
  ecs_service_name          = module.compute.ecs_service_name
}

module "backup" {
  source = "../../modules/backup"

  project_name              = var.project_name
  environment               = var.environment
  source_bucket_id          = module.storage.models_bucket_id
  source_bucket_arn         = module.storage.models_bucket_arn
  destination_bucket_id     = "${var.project_name}-${var.environment}-backup-models"
  destination_bucket_arn    = "arn:aws:s3:::${var.project_name}-${var.environment}-backup-models"
  enable_replication        = false  # Em dev, desabilitar para economizar
  enable_mfa_delete         = false
  backup_schedule           = "cron(0 3 ? * * *)"  # 3 AM UTC
  backup_retention_days     = 7
  cold_storage_after_days   = 3
  backup_resources          = []  # Sem backups em dev
}
