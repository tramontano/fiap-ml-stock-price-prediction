# Guia de Testes Locais (LocalStack)

O **LocalStack** é uma ferramenta fantástica que emula os serviços da AWS localmente. Adicionámo-lo ao nosso `docker-compose.yml` para permitir o teste do nosso código Terraform (`deploy/terraform`) sem gastar um único cêntimo na AWS real.

---

## 1. Como iniciar o ambiente AWS Local

Execute o Docker Compose na raiz do seu projeto. Ele vai iniciar a API, o MinIO (Data Lake local) e agora o **LocalStack** (AWS emulada).

```bash
docker compose up -d localstack
```

Verifique se a porta `4566` está ativa. É por essa porta que o Terraform vai comunicar.

---

## 2. Instalar a ferramenta de comunicação (tflocal)

Para não termos de reescrever dezenas de ficheiros do Terraform colocando URLs apontando para o LocalStack (ex: `endpoint = "http://localhost:4566"`), usamos o **`tflocal`**.

O `tflocal` é um "wrapper" oficial da equipa do LocalStack que intercepta os comandos do Terraform e força as chamadas da AWS a irem para a máquina local.

```bash
# Instala via pip
pip install terraform-local
```

---

## 3. Fazendo o Deploy Local

O processo é idêntico a fazer deploy na AWS real, mas com 3 diferenças cruciais:
1. Usamos `tflocal` em vez de `terraform`.
2. Não precisa de credenciais válidas da AWS.
3. Não tem custos.

```bash
# Navegue até o ambiente de desenvolvimento
cd deploy/terraform/environments/dev

# Configure credenciais falsas temporárias no seu terminal (Opcional, mas recomendado)
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export AWS_DEFAULT_REGION="us-east-1"

# Inicia o backend do terraform e cria os recursos na memória do LocalStack
tflocal init
tflocal plan
tflocal apply -auto-approve
```

---

## Limitações Importantes (Versão Free)

O LocalStack está a correr na versão *Free/Community*. Isto significa que:

**O que vai funcionar:** Criação da VPC, Subnets, IAM Roles, Security Groups, Repositório ECR e Buckets S3. Você consegue navegar nos buckets usando a AWS CLI emulada (`awslocal s3 ls`).

**O que NÃO vai funcionar totalmente:** O ECS Fargate Data Plane.
A criação do cluster e das definições da tarefa vai dar "Sucesso" no Terraform (porque a API do ECS existe na versão free), mas o LocalStack não vai puxar a imagem do Docker e criar um container real. Para que o Fargate e o Application Load Balancer emulem containers reais respondendo a tráfego HTTP, seria necessária a subscrição Pro do LocalStack.

**Conclusão:** Use o LocalStack para validar a sintaxe do Terraform, a ligação entre módulos, as regras de IAM e a estrutura dos buckets. Mas para testar a API em si (com tráfego e inferência de modelos), com isso continuaremos a usar o serviço `web` tradicional via `docker-compose.yml`.
