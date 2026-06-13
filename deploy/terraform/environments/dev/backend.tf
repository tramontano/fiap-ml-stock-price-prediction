# =============================================================================
# Ambiente DEV — Configuração do State
# Salva o arquivo .tfstate no S3 e usa o DynamoDB para evitar deploys simultâneos.
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "fiap-mlops-tfstate-bucket" # OBS: Este bucket deve ser criado antes via console ou cli
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"      # Tabela com Partition Key "LockID" (String)
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
