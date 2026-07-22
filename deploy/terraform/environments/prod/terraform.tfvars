# =============================================================================
# Ambiente PROD — Valores Reais
# =============================================================================

project_name = "fiap-mlops"
environment  = "production"
aws_region   = "us-east-1"

# Dimensionamento robusto para produção
task_cpu     = 1024  # 1 vCPU
task_memory  = 2048  # 2 GB RAM
min_capacity = 2     # Sempre rodando pelo menos 2 instâncias para HA
max_capacity = 10    # Escala até 10 instâncias em pico

vpc_cidr     = "10.0.0.0/16" # CIDR distinto de dev
