# =============================================================================
# Ambiente PROD — Orquestração de Módulos
# Produção prioriza segurança, imutabilidade e alta disponibilidade.
# =============================================================================

module "networking" {
  source = "../../modules/networking"

  project_name           = var.project_name
  environment            = var.environment
  vpc_cidr               = var.vpc_cidr
  azs                    = ["${var.aws_region}a", "${var.aws_region}b"]
  public_subnet_cidrs    = [cidrsubnet(var.vpc_cidr, 8, 1), cidrsubnet(var.vpc_cidr, 8, 2)]
  private_subnet_cidrs   = [cidrsubnet(var.vpc_cidr, 8, 101), cidrsubnet(var.vpc_cidr, 8, 102)]
  nat_gateway_per_az     = true  # Prod: um NAT Gateway por AZ para alta disponibilidade
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
    "ALLOWED_ORIGINS"          = var.allowed_origins
    "MLFLOW_TRACKING_URI"      = var.mlflow_tracking_uri
    "MLFLOW_TRACKING_USERNAME" = var.mlflow_tracking_username
    "MLFLOW_EXPERIMENT_NAME"   = var.mlflow_experiment_name
    "MLFLOW_EXPERIMENT_ID"     = var.mlflow_experiment_id
    "DAGSHUB_REPO_NAME"        = var.dagshub_repo_name
    "API_USERNAME"             = var.api_username
    "API_PASSWORD"             = var.api_password
    "OPTUNA_STORAGE_URI"       = var.optuna_storage_uri != null ? var.optuna_storage_uri : ""
  }

  # Em prod, usar Secrets Manager para credenciais sensíveis (futuro)
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
  enable_memory_scaling       = true   # Prod: escalar também por memória
  memory_target_utilization   = 75
  enable_alb_request_scaling  = true   # Prod: escalar por requisições
  alb_request_count_target    = 1000
  alb_resource_label          = module.compute.alb_resource_label
  enable_custom_metric_scaling = false
  enable_step_scaling         = true   # Prod: ativar step scaling para picos
  step_scaling_cpu_threshold  = 90
  step_scaling_cooldown       = 120
}

module "observability" {
  source = "../../modules/observability"

  project_name              = var.project_name
  environment               = var.environment
  log_retention_days        = 30  # Prod: retenção mais longa
  alarm_5xx_threshold       = 5   # Prod: mais sensível
  alarm_latency_threshold   = 500 # Prod: latência mais rigorosa
  alarm_ecs_cpu_threshold   = 80
  alarm_ecs_memory_threshold = 80
  sns_topic_arn             = var.sns_topic_arn  # Prod: notificações habilitadas
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
  enable_replication        = true   # Prod: ativar replicação cross-region
  enable_mfa_delete         = true   # Prod: proteção máxima
  backup_schedule           = "cron(0 2 ? * * *)"  # 2 AM UTC
  backup_retention_days     = 30
  cold_storage_after_days   = 7
  backup_resources          = []  # Será preenchido conforme necessário
}

module "tls" {
  source = "../../modules/tls"

  project_name                = var.project_name
  environment                 = var.environment
  domain_name                 = var.domain_name
  subject_alternative_names   = var.subject_alternative_names
  validation_method           = "DNS"  # Prod: validação DNS automática
  alb_arn                     = module.compute.alb_arn
  alb_security_group_id       = module.networking.alb_security_group_id
  target_group_arn            = module.compute.target_group_arn
  ssl_policy                  = "ELBSecurityPolicy-TLS-1-2-2017-01"  # Compatibilidade
}
