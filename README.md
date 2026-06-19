# Stock Price Prediction: LSTM para Previsão de Ativos Financeiros

API de previsão de preços de ações desenvolvida como parte do Tech Challenge da Fase 4 da Pós-Graduação em Machine Learning Engineering da FIAP.

## Tabela de Conteúdos

- [Sobre o Projeto](#sobre-o-projeto)
- [Instalando e Executando o Projeto](#instalando-e-executando-o-projeto)
- [Preparando os Dados](#preparando-os-dados)
- [Exemplos de Requisição/Resposta](#exemplos-de-requisiçãoresposta)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Estrutura das Pastas](#estrutura-das-pastas)
- [Gerenciamento de Dependências](#gerenciamento-de-dependências-uv)
- [Infraestrutura com Terraform](#infraestrutura-com-terraform)
- [A API](#a-api)
- [Documentação da API (Endpoints)](#documentação-da-api-endpoints)

## Sobre o Projeto

Este projeto implementa uma solução completa (*end-to-end*) de Machine Learning para prever o preço de fechamento de ativos financeiros utilizando redes neurais profundas (LSTM). O objetivo central é demonstrar como um modelo de Deep Learning sai do ambiente de experimentação (Jupyter Notebook) e ganha vida em um ambiente de produção resiliente, escalável e rastreável.

O sistema foi estruturado seguindo os princípios de **Clean Architecture** e **MLOps**, garantindo:

1. **Reprodutibilidade**: Cada etapa do pipeline é versionada e rastreável através do MLflow/DagsHub.
2. **Escalabilidade**: Infraestrutura containerizada (Docker) e pronta para deploy em nuvem (AWS).
3. **Observabilidade**: Monitoramento contínuo de métricas de negócio (RMSE, MAPE) e infraestrutura (latência, CPU/RAM).
4. **Manutenibilidade**: Código bem estruturado, testável e documentado.

### Objetivo Principal

Prever o preço de fechamento do *ticker* **JNJ** (Johnson & Johnson) utilizando dados históricos de mercado, indicadores técnicos (RSI, EMA) e uma arquitetura LSTM otimizada via Optuna.

### Links da Apresentação

- *[Deploy da API (Produção)](#)*
- *[Documentação Interativa (Swagger)](#)*
- *[Vídeo de Apresentação](#)*

## Instalando e Executando o Projeto

Siga as instruções abaixo para configurar e executar o projeto em seu ambiente local.

### Pré-requisitos

- Python 3.11+
- Git
- Docker + docker-compose
- Make (opcional, para usar `make` commands)
- uv (gerenciador de pacotes Python rápido)

### Execução Local (Stack Completa com Docker Compose)

A forma mais simples de executar o projeto é através do `docker-compose`, que provisiona toda a infraestrutura local (MinIO, PostgreSQL, Prometheus, Grafana, FastAPI).

1. Clone o repositório:

```bash
git clone https://github.com/SEU_USUARIO/fiap-ml-stock-price-prediction.git
cd fiap-ml-stock-price-prediction
```

2. Crie o arquivo de ambiente local a partir do exemplo:

```bash
cp .env.example .env
```

Edite `.env` conforme seu ambiente. Ele não é versionado; o arquivo de referência é `.env.example`.

3. Instale as dependências:

```bash
make install
```

Este comando executa `uv sync`, que instala todas as dependências de forma rápida e determinística.

4. Inicie a infraestrutura local:

```bash
make up
```

Este comando provisiona:
- **MinIO**: Data Lake local simulando AWS S3 (buckets: `bronze`, `silver`, `gold`, `models`)
- **PostgreSQL**: Banco de dados para metadados futuros
- **Prometheus + Grafana**: Stack de observabilidade
- **FastAPI**: Servidor da API

5. Acesse os serviços:

- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (credenciais no `.env`)
- **Grafana**: [http://localhost:3000](http://localhost:3000)
- **API Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Execução Local (FastAPI Apenas)

Se preferir executar apenas a API localmente enquanto usa o MinIO do Docker:

1. Suba apenas o MinIO:

```bash
docker-compose up -d minio postgres
```

2. Ative o ambiente virtual e instale as dependências:

```bash
make install
```

3. Execute a API em modo de desenvolvimento:

```bash
make run
```

A API estará disponível em [http://localhost:8000/docs](http://localhost:8000/docs).

### Parar a Infraestrutura

Para parar todos os containers:

```bash
make down
```

## Preparando os Dados

Antes de treinar o modelo, é necessário popular o Data Lake com dados históricos de mercado.

### 1. Ingestão de Dados (Camada Bronze)

Extrai dados históricos do Yahoo Finance e os salva na camada Bronze do Data Lake:

```bash
make ingest
```

Este comando executa `python -m src.pipelines.ingest_data`, que:
- Baixa dados históricos do *ticker* JNJ via `yfinance`
- Valida os dados
- Salva em formato Parquet no MinIO bucket `bronze`

### 2. Processamento Medallion (Camadas Silver e Gold)

Limpa os dados (Silver) e aplica transformações para gerar indicadores técnicos (Gold):

```bash
make process
```

Este comando executa `python -m src.pipelines.process_data`, que:
- Carrega dados da camada Bronze
- Remove nulos e ordena por data (Silver)
- Calcula retornos diários, RSI e EMA (Gold)
- Salva o resultado enriquecido no MinIO

### 3. Treino e Otimização do Modelo

Treina a rede LSTM com otimização de hiperparâmetros via Optuna:

```bash
make train
```

Este comando executa `python -m src.pipelines.tune_pipeline`, que:
- Carrega dados da camada Gold
- Aplica `StandardScaler` (evitando *data leakage*)
- Executa Optuna com múltiplas *trials* para encontrar os melhores hiperparâmetros
- Registra métricas (RMSE, MAE, MAPE) no MLflow/DagsHub
- Salva o modelo Keras e o pipeline Scikit-Learn como artefatos

### 4. Promoção do Modelo

Avalia as *runs* treinadas e promove a melhor para `Champion`:

```bash
make promote
```

Este comando executa `python -m src.pipelines.promote_model`, que:
- Busca todas as *runs* do experimento `stock-price-lstm` no MLflow
- Identifica a com menor RMSE
- Promove para a tag `Production` (Champion)
- Sincroniza os artefatos para o bucket `models`

## Exemplos de Requisição/Resposta

### Exemplo 1: Health Check

Verifica o status da API e confirma que o modelo está carregado:

```bash
curl -X 'GET' \
  'http://localhost:8000/health' \
  -H 'accept: application/json'
```

Resposta esperada (Status `200 OK`):

```json
{
  "status": "ok",
  "service": "Stock Price Prediction API",
  "version": "1.0.0"
}
```

### Exemplo 2: Realizar Predição

Realiza a predição do preço de fechamento para o *ticker* JNJ:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "ticker": "JNJ"
}'
```

Resposta esperada (Status `200 OK`):

```json
{
  "ticker": "JNJ",
  "predicted_return": -0.0005462466506287456,
  "predicted_return_std_dev": 0.005151910241693258,
  "confidence_score": 74.24044799804688,
  "predicted_price_usd": 238.19982194085242,
  "prediction_date_iso": "2026-06-12T00:00:00",
  "prediction_model": "05b0314cdec24e23be97217429826bb5"
}
```

**Campos da Resposta:**

- `ticker`: Símbolo do ativo analisado
- `predicted_return`: Retorno percentual previsto para o próximo dia
- `predicted_return_std_dev`: Desvio padrão do retorno (incerteza)
- `confidence_score`: Nível de confiança da predição (0-100), calculado via MC Dropout
- `predicted_price_usd`: Preço de fechamento em USD reconvertido a partir do retorno
- `prediction_date_iso`: Data prevista no formato ISO 8601
- `prediction_model`: ID da *run* do MLflow que gerou a predição

## Arquitetura do Sistema

O projeto implementa uma arquitetura robusta separada em três camadas principais: **Dados**, **Machine Learning** e **Serving**.

### Fluxo de Dados (Arquitetura Medallion)

A solução resolve o problema da não-estacionariedade dos dados financeiros convertendo preços nominais em retornos diários percentuais:

1. **Camada Bronze (Raw)**: Dados brutos extraídos do Yahoo Finance, sem tratamento. Armazenados em Parquet no MinIO.
2. **Camada Silver (Processed)**: Dados limpos, sem valores nulos ou anomalias. Ordenados por data.
3. **Camada Gold (Features)**: Dados transformados por *Custom Transformers* Scikit-Learn, gerando indicadores técnicos (Retornos Diários, RSI, Distâncias de EMA).

### Pipeline de Machine Learning

1. **Ingestão**: Extração de dados via `yfinance` para a camada Bronze.
2. **Transformação**: O `scikit-learn Pipeline` calcula indicadores e normaliza dados, sendo salvo como artefato `.pkl`.
3. **Tuning & Treinamento**: Optuna explora o espaço de hiperparâmetros enquanto o MLflow registra métricas.
4. **Registro**: O modelo vencedor é promovido ao *Model Registry* no DagsHub com a tag `Champion`.

### Serving (API)

A API FastAPI não retreina modelos isoladamente, garantindo mitigação contra *Training-Serving Skew*:

1. Durante o *startup*, a API faz o download do modelo `Champion` e do *pipeline* de *features* do MLflow/DagsHub.
2. Ao receber um `POST /predict`, coleta os dados mais recentes via `yfinance`.
3. Aplica o mesmo *pipeline* de transformação usado no treinamento.
4. Executa a inferência com MC Dropout (múltiplas passadas) para calcular confiança.
5. Reconverte o retorno previsto em preço nominal e retorna a resposta.

## Estrutura das Pastas

O projeto está organizado em módulos principais seguindo os princípios de Clean Architecture:

```bash
fiap-ml-stock-price-prediction/
├── .github/workflows/          # Pipelines de CI/CD (GitHub Actions)
├── deploy/
│   ├── docker/                 # Dockerfiles (API, Airflow)
│   └── terraform/              # Infraestrutura como Código (IaC)
│       ├── modules/            # Módulos reutilizáveis (compute, storage, iam, etc.)
│       └── environments/       # Configurações por ambiente (dev, prod)
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   ├── PRD.md                  # Product Requirements Document
│   ├── architecture.md         # Visão técnica da arquitetura
│   ├── TODO.md                 # Lista de tarefas e roadmap
│   └── repository.md           # Documentação do repositório
├── src/                        # Código-fonte principal
│   ├── api/                    # [Apresentação] Rotas FastAPI
│   ├── core/                   # [Configuração] Variáveis globais e logging
│   ├── domain/                 # [Domínio] Contratos Pydantic
│   ├── infrastructure/         # [Infraestrutura] Adaptadores S3/MinIO
│   ├── ml/                     # [Core ML] LSTM, Features e MC Dropout
│   └── pipelines/              # [Casos de Uso] Ingestão, processamento, tuning
├── tests/                      # Testes unitários e de integração
├── docker-compose.yml          # Stack local (MinIO, FastAPI, Prometheus, Grafana)
├── Dockerfile                  # Imagem Docker para produção
├── Makefile                    # Interface principal de comandos
├── pyproject.toml              # Gerenciamento de dependências
└── README.md
```

## Gerenciamento de Dependências (`uv`)

O projeto utiliza **uv** como gerenciador de pacotes e ambientes virtuais Python.

### Por que `uv`?

Conforme documentado no ADR 0002, o `uv` foi escolhido por:

- **Velocidade**: Redução drástica no tempo de resolução de dependências e instalação de pacotes.
- **Reprodutibilidade**: Arquivo de *lock* determinístico (`uv.lock`) garantindo paridade entre desenvolvimento e produção.
- **Simplicidade**: Respeita o padrão `pyproject.toml` sem configurações excessivamente opinativas.

### Comandos Principais

```bash
# Instalar dependências
make install

# Adicionar nova dependência
uv add <pacote>

# Remover dependência
uv remove <pacote>

# Sincronizar ambiente
uv sync

# Executar comando no ambiente virtual
uv run <comando>
```

## Infraestrutura com Terraform

O projeto utiliza **Terraform** para provisionar a infraestrutura na AWS de forma automatizada e versionada (Infrastructure as Code).

### Arquitetura na Nuvem

A infraestrutura provisiona um ambiente escalável e seguro para servir o modelo de Machine Learning:

- **Networking**: VPC própria, Subnets Públicas (ALB) e Privadas (ECS)
- **Compute (Serving)**: ECS com Fargate (Serverless Containers) + Application Load Balancer (ALB)
- **Storage**: Buckets S3 divididos nas camadas Medallion (`bronze`, `silver`, `gold`) e bucket versionado para modelos (`models`)
- **ECR**: Repositório Docker privado com verificação de vulnerabilidades
- **IAM**: Princípio do menor privilégio

### Estrutura do Terraform

```bash
deploy/terraform/
├── modules/                    # Blocos reutilizáveis
│   ├── compute/                # ECS Fargate, ALB, Auto Scaling
│   ├── ecr/                    # Elastic Container Registry
│   ├── iam/                    # Políticas de Segurança
│   ├── networking/             # VPC, Subnets, NAT Gateway
│   └── storage/                # Buckets S3, Encriptação, Lifecycle
├── environments/               # Instanciação dos módulos
│   ├── dev/                    # Ambiente de Desenvolvimento
│   └── prod/                   # Ambiente de Produção
└── README.md                   # Documentação detalhada
```

### Passo a Passo na AWS

1. **Configurar variáveis**

Edite `deploy/terraform/environments/dev/terraform.tfvars`:

```hcl
aws_region         = "us-east-1"
project_name       = "fiap-ml-stock-price-prediction"
environment        = "dev"
```

2. **Inicializar o Terraform**

```bash
cd deploy/terraform/environments/dev
terraform init
```

3. **Validar a configuração**

```bash
terraform validate
```

4. **Visualizar o plano de execução**

```bash
terraform plan
```

5. **Aplicar a infraestrutura**

```bash
terraform apply
```

Este comando irá:
- Criar o repositório ECR
- Provisionar a instância ECS Fargate
- Configurar o Application Load Balancer
- Criar os buckets S3
- Configurar as políticas IAM

6. **Visualizar outputs**

```bash
terraform output
```

Principais outputs:
- `alb_dns_name`: URL pública da API
- `ecr_repository_url`: URL do repositório ECR

Para mais detalhes, consulte o [README do Terraform](deploy/terraform/README.md).

## A API

A API foi desenvolvida utilizando **FastAPI** seguindo os princípios da **Clean Architecture**.

### Estrutura Interna

```bash
src/
├── api/                        # Camada de Apresentação
│   ├── main.py                 # Ponto de entrada (lifespan, middlewares)
│   └── routes.py               # Definição dos endpoints
├── core/                       # Configurações Globais
│   ├── config.py               # Variáveis de ambiente
│   └── logging.py              # Logging estruturado
├── domain/                     # Contratos de Dados
│   └── schemas.py              # Modelos Pydantic
├── infrastructure/             # Adaptadores Externos
│   └── storage_client.py       # Cliente S3/MinIO
├── ml/                         # Lógica de Machine Learning
│   ├── inference.py            # Orquestrador de inferência
│   ├── features.py             # Engenharia de features
│   ├── model.py                # Arquitetura LSTM
│   └── transformers.py         # Transformadores customizados
└── pipelines/                  # Casos de Uso
    ├── ingest_data.py          # Extração de dados
    ├── process_data.py         # Processamento Medallion
    ├── tune_pipeline.py        # Treino e otimização
    └── promote_model.py        # Promoção de modelos
```

### Clean Architecture

Este projeto segue os princípios da Clean Architecture, onde as dependências sempre apontam de fora para dentro. Isso significa que as camadas internas (regras de negócio) não conhecem as camadas externas (frameworks, banco de dados, UI).

**Benefícios:**

- **Independência de Frameworks**: A lógica de negócio não depende do FastAPI
- **Testabilidade**: Cada camada pode ser testada isoladamente
- **Manutenibilidade**: Mudanças em uma camada não afetam as outras
- **Escalabilidade**: Fácil adicionar novas funcionalidades

### Componentes Principais

#### 1. **Configuração (`core/config.py`)**

Gerencia todas as configurações da aplicação usando variáveis de ambiente e `pydantic_settings`.

#### 2. **Logging Estruturado (`core/logging.py`)**

Implementa logging em JSON com rastreamento de `request_id`, latência e erros.

#### 3. **Storage Client (`infrastructure/storage_client.py`)**

Abstração para armazenamento S3/MinIO com métodos para download/upload e operações com Parquet.

#### 4. **Inferência (`ml/inference.py`)**

Orquestrador central que:
- Busca o modelo `Champion` no MLflow/DagsHub
- Aplica o *pipeline* de transformação em tempo real
- Executa MC Dropout para calcular confiança
- Reconverte retornos em preços

#### 5. **Transformadores Customizados (`ml/transformers.py`)**

Classes Scikit-Learn para calcular:
- `DailyReturnTransformer`: Retornos percentuais diários
- `RSITransformer`: Índice de Força Relativa
- `EMATransformer`: Distâncias de Médias Móveis Exponenciais

### Dependências Principais

```
fastapi = 0.115.2              # Framework web
uvicorn = 0.30.3               # Servidor ASGI
tensorflow = 2.15.0            # Deep Learning
scikit-learn = 1.5.0           # Machine Learning
optuna = 3.6.0                 # Hyperparameter tuning
mlflow = 2.14.0                # Model tracking
yfinance = 0.2.41              # Dados financeiros
boto3 = 1.34.0                 # AWS SDK
```

### Executando a API

A forma recomendada é usar o **Makefile**:

```bash
make run
```

Alternativamente, execute diretamente:

```bash
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Documentação da API (Endpoints)

Abaixo estão os endpoints implementados no projeto.

> URL base: `/api/v1`

### Rotas Abertas (sem autenticação)

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| GET | `/health` | Verifica o status da API e confirma que o modelo está carregado. |
| POST | `/predict` | Realiza a predição do preço de fechamento para um *ticker*. |
| GET | `/metrics` | Expõe métricas Prometheus para monitoramento. |

### Estrutura de Requisição

**POST `/predict`**

```json
{
  "ticker": "JNJ"
}
```

### Estrutura de Resposta

```json
{
  "ticker": "JNJ",
  "predicted_return": 0.0125,
  "predicted_return_std_dev": 0.0045,
  "confidence_score": 87.5,
  "predicted_price_usd": 156.42,
  "prediction_date_iso": "2026-06-15",
  "prediction_model": "stock-price-lstm-run-abc123"
}
```

---

**Desenvolvido como parte do Tech Challenge - Fase 4 da Pós Tech FIAP.**
