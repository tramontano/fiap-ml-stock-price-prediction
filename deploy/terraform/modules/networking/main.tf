# =============================================================================
# Módulo: Networking — VPC, Subnets, NAT Gateway, Security Groups
#
# Arquitetura:
#   Internet → IGW → Public Subnet (ALB) → Private Subnet (ECS Fargate)
#                                             ↓
#                                        NAT Gateway → Internet (saída)
#
# As subnets privadas NÃO recebem tráfego da internet diretamente.
# O tráfego de saída (ex: download do modelo do S3) passa pelo NAT Gateway.
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Module      = "networking"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# VPC — Rede privada isolada na AWS
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Internet Gateway — Porta de entrada para a internet (subnets públicas)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-igw"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Subnets Públicas — ALB (Application Load Balancer)
# Distribuídas em múltiplas AZs para alta disponibilidade.
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-${var.azs[count.index]}"
    Tier = "public"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Subnets Privadas — ECS Fargate (containers da API LSTM)
# Invisíveis para o mundo externo. Saída para a internet via NAT Gateway.
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-${var.azs[count.index]}"
    Tier = "private"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# NAT Gateway — Permite que as subnets privadas façam requests para a internet
# (ex: download do modelo do S3, chamadas ao yfinance) sem serem acessíveis.
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-eip"
  })
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id # Associado à primeira subnet pública

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-gw"
  })

  depends_on = [aws_internet_gateway.main]
}

# ─────────────────────────────────────────────────────────────────────────────
# Route Tables — Regras de roteamento para cada tipo de subnet
# ─────────────────────────────────────────────────────────────────────────────

# Pública: tráfego 0.0.0.0/0 vai para o Internet Gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rt-public"
  })
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Privada: tráfego 0.0.0.0/0 vai para o NAT Gateway (saída segura)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rt-private"
  })
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ─────────────────────────────────────────────────────────────────────────────
# Security Groups — Firewall da VPC
# ─────────────────────────────────────────────────────────────────────────────

# SG do ALB: aceita HTTP (80) e HTTPS (443) de qualquer origem
resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-sg-alb"
  description = "Permite trafego HTTP/HTTPS de entrada no ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Saida irrestrita"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-sg-alb"
  })
}

# SG do ECS: aceita tráfego SOMENTE do ALB na porta 8000 (FastAPI/Uvicorn)
resource "aws_security_group" "ecs" {
  name        = "${local.name_prefix}-sg-ecs"
  description = "Permite trafego apenas do ALB na porta 8000"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "FastAPI via ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Saida irrestrita (S3, yfinance, DagsHub)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-sg-ecs"
  })
}
