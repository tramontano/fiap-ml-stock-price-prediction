#!/bin/bash

# =============================================================================
# Script de Teste de Endpoints da API
# Testa: Health Check, Autenticação, Endpoints Principais
# =============================================================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configurações
API_URL="${1:-http://localhost:8001}"
API_USERNAME="${2:-admin}"
API_PASSWORD="${3:-password}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Teste de Endpoints da API${NC}"
echo -e "${BLUE}URL: ${API_URL}${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ─────────────────────────────────────────────────────────────────────────
# 1. Health Check
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Testando Health Check...${NC}"

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/v1/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  echo -e "${GREEN}✓ Health Check OK${NC}"
  echo -e "Response: $BODY\n"
else
  echo -e "${RED}✗ Health Check falhou (HTTP $HTTP_CODE)${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# 2. Autenticação (Login)
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Testando Autenticação...${NC}"

AUTH_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"${API_USERNAME}\", \"password\": \"${API_PASSWORD}\"}" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
BODY=$(echo "$AUTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  echo -e "${GREEN}✓ Autenticação OK${NC}"
  TOKEN=$(echo "$BODY" | jq -r '.access_token' 2>/dev/null || echo "")
  echo -e "Token obtido: ${TOKEN:0:20}...\n"
else
  echo -e "${RED}✗ Autenticação falhou (HTTP $HTTP_CODE)${NC}"
  echo -e "Response: $BODY\n"
  TOKEN=""
fi

# ─────────────────────────────────────────────────────────────────────────
# 3. Listar Modelos
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/5] Testando Listagem de Modelos...${NC}"

MODELS_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${API_URL}/api/v1/models")

HTTP_CODE=$(echo "$MODELS_RESPONSE" | tail -n1)
BODY=$(echo "$MODELS_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  echo -e "${GREEN}✓ Listagem de Modelos OK${NC}"
  MODEL_COUNT=$(echo "$BODY" | jq '.models | length' 2>/dev/null || echo "0")
  echo -e "Modelos encontrados: $MODEL_COUNT\n"
else
  echo -e "${YELLOW}⚠ Listagem de Modelos retornou HTTP $HTTP_CODE${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# 4. Fazer Predição
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/5] Testando Endpoint de Predição...${NC}"

# Dados de exemplo (ajuste conforme sua API)
PREDICTION_DATA='{
  "ticker": "PETR4.SA",
  "lookback_days": 30,
  "forecast_days": 5
}'

PREDICTION_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PREDICTION_DATA" \
  -w "\n%{http_code}" \
  "${API_URL}/api/v1/predict")

HTTP_CODE=$(echo "$PREDICTION_RESPONSE" | tail -n1)
BODY=$(echo "$PREDICTION_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
  echo -e "${GREEN}✓ Predição OK${NC}"
  echo -e "Response: $(echo $BODY | jq '.' 2>/dev/null | head -5)\n"
elif [ "$HTTP_CODE" == "422" ]; then
  echo -e "${YELLOW}⚠ Validação de entrada falhou (HTTP 422)${NC}"
  echo -e "Ajuste os dados de entrada conforme a API\n"
else
  echo -e "${RED}✗ Predição falhou (HTTP $HTTP_CODE)${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# 5. Métricas/Status
# ─────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Testando Métricas...${NC}"

METRICS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/metrics")
HTTP_CODE=$(echo "$METRICS_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" == "200" ]; then
  echo -e "${GREEN}✓ Métricas Prometheus disponíveis${NC}\n"
else
  echo -e "${YELLOW}⚠ Endpoint /metrics retornou HTTP $HTTP_CODE${NC}\n"
fi

# ─────────────────────────────────────────────────────────────────────────
# Resumo
# ─────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Testes concluídos!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}Checklist de Validação:${NC}"
echo -e "□ Health Check respondendo"
echo -e "□ Autenticação funcionando"
echo -e "□ Modelos listáveis"
echo -e "□ Predições funcionando"
echo -e "□ Métricas disponíveis"
echo -e ""
echo -e "${YELLOW}Monitoramento:${NC}"
echo -e "• CloudWatch Logs: /ecs/fiap-mlops-prod-api"
echo -e "• CloudWatch Metrics: CPU, Memory, Request Count"
echo -e "• Prometheus: ${API_URL}/metrics"
