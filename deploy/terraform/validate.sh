#!/bin/bash

# =============================================================================
# Script de Validação da Infraestrutura AWS
# Valida: Health Checks, Endpoints, Segurança, Performance
# =============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
ENVIRONMENT="${1:-dev}"
AWS_REGION="${2:-us-east-1}"
CLUSTER_NAME="fiap-mlops-${ENVIRONMENT}"
SERVICE_NAME="fiap-mlops-${ENVIRONMENT}-api"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Validação de Infraestrutura AWS${NC}"
echo -e "${BLUE}Ambiente: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Região: ${AWS_REGION}${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ─────────────────────────────────────────────────────────────────────────
# 1. Validar ECS Cluster
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/8] Validando ECS Cluster...${NC}"
CLUSTER_STATUS=$(aws ecs describe-clusters \
  --clusters ${CLUSTER_NAME} \
  --region ${AWS_REGION} \
  --query 'clusters[0].status' \
  --output text 2>/dev/null || echo "NOTFOUND")

if [ "$CLUSTER_STATUS" == "ACTIVE" ]; then
  echo -e "${GREEN}✓ Cluster ${CLUSTER_NAME} está ATIVO${NC}\n"
else
  echo -e "${RED}✗ Cluster ${CLUSTER_NAME} não encontrado ou inativo${NC}"
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────
# 2. Validar ECS Service
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/8] Validando ECS Service...${NC}"
SERVICE_INFO=$(aws ecs describe-services \
  --cluster ${CLUSTER_NAME} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'services[0]' \
  --output json)

RUNNING_COUNT=$(echo $SERVICE_INFO | jq '.runningCount')
DESIRED_COUNT=$(echo $SERVICE_INFO | jq '.desiredCount')
SERVICE_STATUS=$(echo $SERVICE_INFO | jq -r '.status')

echo -e "Service Status: ${SERVICE_STATUS}"
echo -e "Running Tasks: ${RUNNING_COUNT}/${DESIRED_COUNT}"

if [ "$RUNNING_COUNT" -ge 1 ]; then
  echo -e "${GREEN}✓ Service está rodando com ${RUNNING_COUNT} tasks${NC}\n"
else
  echo -e "${RED}✗ Nenhuma task rodando no service${NC}"
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────
# 3. Validar ALB Health Check
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/8] Validando ALB Health Check...${NC}"

# Obter ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --region ${AWS_REGION} \
  --query "LoadBalancers[?contains(LoadBalancerName, '${ENVIRONMENT}')].LoadBalancerArn" \
  --output text | head -1)

if [ -z "$ALB_ARB" ]; then
  echo -e "${YELLOW}⚠ ALB não encontrado, pulando health check${NC}\n"
else
  # Obter Target Group
  TG_ARN=$(aws elbv2 describe-target-groups \
    --load-balancer-arn ${ALB_ARN} \
    --region ${AWS_REGION} \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

  # Verificar saúde dos targets
  HEALTHY_TARGETS=$(aws elbv2 describe-target-health \
    --target-group-arn ${TG_ARN} \
    --region ${AWS_REGION} \
    --query 'TargetHealthDescriptions[?TargetHealth.State==`healthy`] | length(@)' \
    --output text)

  TOTAL_TARGETS=$(aws elbv2 describe-target-health \
    --target-group-arn ${TG_ARN} \
    --region ${AWS_REGION} \
    --query 'TargetHealthDescriptions | length(@)' \
    --output text)

  echo -e "Targets Saudáveis: ${HEALTHY_TARGETS}/${TOTAL_TARGETS}"

  if [ "$HEALTHY_TARGETS" -ge 1 ]; then
    echo -e "${GREEN}✓ ALB Health Check passou${NC}\n"
  else
    echo -e "${YELLOW}⚠ Nenhum target saudável, aguarde alguns minutos${NC}\n"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────
# 4. Validar CloudWatch Logs
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/8] Validando CloudWatch Logs...${NC}"

LOG_GROUP="/ecs/fiap-mlops-${ENVIRONMENT}-api"
LOG_STREAMS=$(aws logs describe-log-streams \
  --log-group-name ${LOG_GROUP} \
  --region ${AWS_REGION} \
  --query 'logStreams | length(@)' \
  --output text 2>/dev/null || echo "0")

if [ "$LOG_STREAMS" -gt 0 ]; then
  echo -e "${GREEN}✓ CloudWatch Log Group com ${LOG_STREAMS} streams${NC}\n"
  
  # Mostrar últimos logs
  echo -e "${BLUE}Últimos logs:${NC}"
  aws logs tail ${LOG_GROUP} --follow --since 5m --region ${AWS_REGION} | head -20
else
  echo -e "${YELLOW}⚠ Nenhum log stream encontrado ainda${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# 5. Validar S3 Buckets
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/8] Validando S3 Buckets...${NC}"

BUCKETS=$(aws s3 ls --region ${AWS_REGION} | grep "fiap-mlops-${ENVIRONMENT}" | wc -l)

if [ "$BUCKETS" -ge 3 ]; then
  echo -e "${GREEN}✓ S3 Buckets encontrados (${BUCKETS})${NC}"
  aws s3 ls --region ${AWS_REGION} | grep "fiap-mlops-${ENVIRONMENT}"
  echo -e ""
else
  echo -e "${RED}✗ Menos de 3 buckets encontrados${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# 6. Validar ECR Repository
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[6/8] Validando ECR Repository...${NC}"

ECR_REPO=$(aws ecr describe-repositories \
  --region ${AWS_REGION} \
  --query "repositories[?contains(repositoryName, '${ENVIRONMENT}')].repositoryUri" \
  --output text | head -1)

if [ -n "$ECR_REPO" ]; then
  echo -e "${GREEN}✓ ECR Repository: ${ECR_REPO}${NC}\n"
else
  echo -e "${RED}✗ ECR Repository não encontrado${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# 7. Validar Security Groups
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[7/8] Validando Security Groups...${NC}"

SG_COUNT=$(aws ec2 describe-security-groups \
  --region ${AWS_REGION} \
  --filters "Name=tag:Environment,Values=${ENVIRONMENT}" \
  --query 'SecurityGroups | length(@)' \
  --output text)

if [ "$SG_COUNT" -ge 2 ]; then
  echo -e "${GREEN}✓ Security Groups configurados (${SG_COUNT})${NC}\n"
else
  echo -e "${YELLOW}⚠ Apenas ${SG_COUNT} Security Groups encontrados${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# 8. Validar Certificado ACM (se prod)
# ─────────────────────────────────────────────────────────────────────────
if [ "$ENVIRONMENT" == "prod" ]; then
  echo -e "${YELLOW}[8/8] Validando Certificado ACM...${NC}"

  CERT_STATUS=$(aws acm list-certificates \
    --region ${AWS_REGION} \
    --query "CertificateSummaryList[0].Status" \
    --output text 2>/dev/null || echo "NOTFOUND")

  if [ "$CERT_STATUS" == "ISSUED" ]; then
    echo -e "${GREEN}✓ Certificado ACM emitido${NC}\n"
  elif [ "$CERT_STATUS" == "PENDING_VALIDATION" ]; then
    echo -e "${YELLOW}⚠ Certificado aguardando validação DNS${NC}\n"
  else
    echo -e "${RED}✗ Certificado não encontrado ou com erro${NC}\n"
  fi
else
  echo -e "${YELLOW}[8/8] Pulando validação de certificado (dev)${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# Resumo Final
# ─────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Validação concluída com sucesso!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}Próximos passos:${NC}"
echo -e "1. Aguarde a propagação DNS (24-48 horas)"
echo -e "2. Teste a API: curl https://api.seu-dominio.com/api/v1/health"
echo -e "3. Monitore os logs: aws logs tail /ecs/fiap-mlops-${ENVIRONMENT}-api --follow"
echo -e "4. Verifique o CloudWatch Dashboard"
