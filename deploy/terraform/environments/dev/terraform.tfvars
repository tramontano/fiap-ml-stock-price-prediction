# =============================================================================
# Ambiente DEV — Valores Reais
# =============================================================================

project_name = "fiap-mlops"
environment  = "dev"
aws_region   = "us-east-1"

# Dimensionamento reduzido para ambiente de desenvolvimento (cortar custos)
task_cpu     = 256
task_memory  = 512
min_capacity = 1
max_capacity = 2

vpc_cidr     = "10.1.0.0/16" # CIDR distinto de prod para evitar conflitos de peering
