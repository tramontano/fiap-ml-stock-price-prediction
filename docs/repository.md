
# Estrutura do repositório

```text
fiap-ml-stock-price-prediction/
├── .github/
│   └── workflows/          # Pipelines de CI/CD (GitHub Actions)
├── airflow/
│   └── dags/               # Orquestração do retreinamento (chamam os scripts do src/pipelines)
├── data/                   # Diretório ignorado pelo git (gerenciado via DVC)
│   ├── raw/                # Bronze
│   ├── processed/          # Silver
│   └── features/           # Gold
├── notebooks/              # Prototipagem e EDA (apenas Jupyter, sem código de produção)
├── src/                    # Código-fonte da aplicação (Pacote principal)
│   ├── api/                # [Apresentação] Rotas FastAPI, dependências e middlewares
│   ├── core/               # Configurações globais (pydantic BaseSettings, logging)
│   ├── domain/             # [Domínio] Modelos de dados (Pydantic schemas: StockRequest, PredictionResponse)
│   ├── infrastructure/     # [Infraestrutura] Adaptadores externos (Minio/S3 Client, yfinance wrapper, MLflow/DagsHub logger)
│   ├── ml/                 # Lógica de ML isolada (definição do LSTM, classes de feature engineering/scaling)
│   └── pipelines/          # [Aplicação/Casos de Uso] Scripts que orquestram ingestão, treino e avaliação
├── terraform/              # Infraestrutura como código (S3, ECS, IAM)
├── tests/                  # Testes automatizados (Pytest)
│   ├── unit/
│   └── integration/
├── .env.example            # Template de variáveis de ambiente
├── .gitignore
├── docker-compose.yml      # Stack local (MinIO, FastAPI)
├── Dockerfile              # Construção da imagem para produção (ECS Fargate)
├── Makefile                # Atalhos para comandos (make train, make serve, make test)
└── pyproject.toml          # Gerenciamento de pacotes e dependências
```
