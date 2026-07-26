# Guia de Deployment e Operações (AWS)

Este guia descreve os passos necessários para realizar o deploy da infraestrutura e da aplicação na AWS, bem como os procedimentos operacionais padrão.

---

## 1. Pré-requisitos

Antes de iniciar qualquer deploy, garanta que você possui:

1. **Conta AWS** com permissões administrativas.
2. **AWS CLI** instalado e configurado (`aws configure`).
3. **Terraform** (versão 1.6.0 ou superior) instalado.
4. **Docker** instalado e em execução.
5. Um **Domínio** registrado (Route53 ou externo) para configuração do HTTPS.

---

## 2. Preparação do Estado Remoto (Backend)

O Terraform precisa de um bucket S3 e uma tabela DynamoDB para armazenar o estado e gerenciar locks de concorrência.

```bash
# Crie o bucket S3 (substitua pelo nome desejado)
aws s3api create-bucket \
  --bucket fiap-mlops-terraform-state \
  --region us-east-1

# Habilite versionamento no bucket
aws s3api put-bucket-versioning \
  --bucket fiap-mlops-terraform-state \
  --versioning-configuration Status=Enabled

# Crie a tabela DynamoDB para state locking
aws dynamodb create-table \
  --table-name fiap-mlops-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

---

## 3. Deployment da Infraestrutura (Terraform)

A infraestrutura deve ser provisionada *antes* da aplicação.

### 3.1. Ambiente de Desenvolvimento (Dev)

```bash
cd deploy/terraform/environments/dev

# Inicializar o Terraform
terraform init

# Validar o código
terraform validate

# Planejar a execução
terraform plan -out=tfplan

# Aplicar a infraestrutura
terraform apply tfplan
```

### 3.2. Ambiente de Produção (Prod)

Em produção, injetamos credenciais sensíveis no momento do plan/apply:

```bash
cd deploy/terraform/environments/prod

terraform init

terraform plan \
  -var="mlflow_tracking_username=seu_usuario" \
  -var="mlflow_tracking_password=seu_token" \
  -var="api_username=admin" \
  -var="api_password=senha_forte" \
  -var="dagshub_app_token=seu_token_dagshub" \
  -out=tfplan

terraform apply tfplan
```

---

## 4. Deployment da Aplicação (Docker/ECR)

Após a infraestrutura estar pronta, o ECR estará disponível para receber a imagem Docker.

```bash
# Obtenha o URI do repositório ECR (substitua pelos seus dados)
ECR_URI="123456789012.dkr.ecr.us-east-1.amazonaws.com/fiap-mlops-prod-ecr"

# Autentique o Docker no ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI

# Faça o build da imagem
docker build -t fiap-mlops-api:v1.0.0 .

# Faça a tag da imagem para o ECR
docker tag fiap-mlops-api:v1.0.0 $ECR_URI:v1.0.0

# Faça o push da imagem
docker push $ECR_URI:v1.0.0
```

Para atualizar o serviço ECS para usar a nova imagem:

```bash
aws ecs update-service \
  --cluster fiap-mlops-prod \
  --service fiap-mlops-prod-api \
  --force-new-deployment \
  --region us-east-1
```

---

## 5. CI/CD (GitHub Actions)

Os workflows do GitHub Actions estão configurados em `.github/workflows/`.

### Secrets Necessários no GitHub:
Para que as pipelines funcionem, configure os seguintes *Repository Secrets*:

- `AWS_ROLE_TO_ASSUME_DEV`: ARN da IAM Role de Dev para o GitHub Actions assumir (via OIDC).
- `AWS_ROLE_TO_ASSUME_PROD`: ARN da IAM Role de Prod.
- `MLFLOW_USERNAME`: Usuário do MLflow/DagsHub.
- `MLFLOW_PASSWORD`: Senha/Token do MLflow/DagsHub.
- `API_USERNAME`: Usuário admin da API.
- `API_PASSWORD`: Senha admin da API.
- `DAGSHUB_TOKEN`: Token da App DagsHub.
- `SLACK_WEBHOOK_URL`: (Opcional) Webhook para notificações de deploy.

---

## 6. Scripts de Validação e Testes

Para facilitar a validação do ambiente, criamos dois scripts utilitários na pasta `deploy/terraform/`:

### 6.1. Validar Infraestrutura (`validate.sh`)
Verifica se todos os recursos da AWS foram provisionados corretamente e estão saudáveis.

```bash
# Validar ambiente de desenvolvimento
./validate.sh dev us-east-1

# Validar ambiente de produção
./validate.sh prod us-east-1
```

### 6.2. Testar Endpoints da API (`test-endpoints.sh`)
Executa chamadas HTTP para verificar se a API está respondendo e processando predições.

```bash
# Substitua pela URL real do seu ALB ou domínio
./test-endpoints.sh https://api.seu-dominio.tk seu_usuario sua_senha
```

---

## 7. Checklist de Produção (Go-Live)

Antes de abrir o tráfego para os usuários finais, valide:

### Segurança
- [ ] O AWS Secrets Manager está armazenando todas as credenciais corretamente.
- [ ] O certificado ACM está emitido e associado ao ALB.
- [ ] O listener HTTP (80) está redirecionando para HTTPS (443).
- [ ] As Security Groups permitem acesso apenas nas portas necessárias.
- [ ] As tags Docker no ECR estão configuradas como Imutáveis.

### Resiliência
- [ ] O NAT Gateway está provisionado em múltiplas AZs.
- [ ] O Auto Scaling (Target Tracking e Step Scaling) está configurado e ativo.
- [ ] O bucket S3 de produção tem versionamento e MFA Delete ativados.
- [ ] A replicação Cross-Region (CRR) do S3 está ativa.
- [ ] O AWS Backup está agendado (diário) e cobrindo os recursos necessários.

### Observabilidade
- [ ] Os logs da aplicação estão fluindo para o CloudWatch Log Groups.
- [ ] O CloudWatch Dashboard está exibindo métricas de CPU, Memória e Latência.
- [ ] Os alarmes (5xx, Latência Alta, CPU Alta) estão configurados e o tópico SNS tem assinantes.

---

## 8. Procedimentos de Disaster Recovery (DR)

### 8.1. Recuperação de Modelos Deletados (S3)
Como o versionamento está ativo, se um modelo for deletado acidentalmente, o S3 apenas insere um *Delete Marker*.
1. Acesse o console do S3.
2. Ative a visualização de "Show versions".
3. Delete o *Delete Marker* para restaurar o arquivo original.

### 8.2. Falha de Região (Region Outage)
Se a região `us-east-1` cair completamente:
1. Os dados e modelos já estarão replicados no bucket de backup em `us-west-2` (via CRR).
2. Execute o Terraform aplicando o ambiente de DR (a ser criado) na região secundária.
3. Atualize o DNS (Route53) para apontar para o novo ALB na região secundária.
