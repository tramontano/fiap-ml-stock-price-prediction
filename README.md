# Stock Price Prediction: Modelagem LSTM para Previsao de Ativos Financeiros

Este projeto consiste em um sistema de Machine Learning end-to-end projetado para prever o preco de fechamento de ativos financeiros, utilizando redes neurais recorrentes do tipo Long Short-Term Memory (LSTM). O desenvolvimento desta solucao foi realizado como parte do Tech Challenge da Fase 4 da Pos-Graduacao em Machine Learning Engineering da FIAP.

---

## Introducao e Contextualizacao do Grupo

Durante o desenvolvimento deste projeto, nosso grupo buscou ir alem de um simples modelo preditivo em formato de notebook experimental. Estruturamos uma arquitetura robusta baseada em principios de Clean Architecture e MLOps. O objetivo principal foi mitigar desafios reais enfrentados em ambientes produtivos de mercado financeiro, tais como o training-serving skew e a volatilidade inerente aos ativos.

Para isso, adotamos a premissa de modelar a variacao percentual diaria dos precos (retornos diarios) em vez dos precos nominais absolutos. Essa abordagem garante a estacionariedade da serie temporal, facilitando a convergencia da rede LSTM. Na etapa de Serving, os retornos previstos sao reconvertidos em valores nominais em USD utilizando um preco de fechamento real como ancora.

---

## Arquitetura Geral do Sistema

A solucao e dividida em tres grandes pilares integrados:

### 1. Pipeline de Dados (Arquitetura Medallion)
- Camada Bronze (Raw Data): Extraida diretamente do Yahoo Finance (yfinance) e persistida em formato Parquet no Data Lake.
- Camada Silver (Processed Data): Dados limpos, ordenados cronologicamente e livres de valores ausentes.
- Camada Gold (Feature Store): Contem os indicadores tecnicos e features calculadas por transformadores personalizados compativeis com o Scikit-Learn (Retorno Diario, RSI e Distancias de Medias Moveis Exponenciais).

### 2. Ciclo de Vida de Modelos (MLOps)
- Treinamento e Otimizacao: Realizado em pipelines estruturados utilizando a biblioteca Optuna para busca bayesiana de hiperparametros.
- Rastreabilidade: Integracao nativa com o MLflow e DagsHub para o registro de runs, metricas (RMSE, MAE, MAPE), hyperparametros e artefatos.
- Promocao de Modelos: Lógica automatizada baseada no menor erro quadratico medio (RMSE). O melhor modelo e tagueado como Champion (Producao) e os concorrentes como Challenger.

### 3. Serving de Baixa Latencia (FastAPI)
- Startup Lifespan: No boot da API, o modelo Champion e seu respectivo pipeline de escalonamento (StandardScaler) sao carregados na memoria da aplicacao a partir do S3 local (MinIO).
- Predicao de Ponta a Ponta: A rota `/predict` consome dados recentes em tempo real, executa a transformacao de features utilizando o pipeline original e infere a previsao.
- Score de Confianca (Monte Carlo Dropout): Implementamos a inferencia com a flag training=True na rede LSTM. Realizando multiplas passadas estocasticas de inferencia por requisicao, calculamos a variabilidade (desvio padrao) e definimos um score de confianca rigoroso limitando a tolerancia a desvios.

---

## Instalacao e Requisitos

### Pre-requisitos
- Python 3.11
- Docker e Docker Compose
- uv (gerenciador de dependencias de alta performance para Python)

### Instalacao Inicial
1. Clonar o repositorio:
```bash
git clone https://github.com/tramontano/fiap-ml-stock-price-prediction.git
cd fiap-ml-stock-price-prediction
```

2. Configurar o arquivo de ambiente:
```bash
copy .env.example .env
```

3. Instalar as dependencias de desenvolvimento e producao de forma otimizada via uv:
```bash
make install
```

---

## Atalhos de Execucao (Makefile)

O projeto disponibiliza uma interface uniforme de comandos atraves do Makefile para automatizar as operacoes comuns da suite:

| Comando | Acao Executada |
| :--- | :--- |
| `make install` | Executa a instalacao e sincronizacao de todas as dependencias declaradas via uv. |
| `make start` | Inicia em background todos os containers da infraestrutura local via Docker Compose (MinIO, PostgreSQL, Prometheus e Grafana). |
| `make stop` | Para e destroi todos os containers da infraestrutura local. |
| `make run` | Executa o servidor de desenvolvimento da API FastAPI localmente com hot-reload ativo na porta 8000. |
| `make train` | Dispara o script de treinamento e sintonia de hiperparametros do modelo LSTM. |
| `make promote` | Executa o pipeline de avaliacao que compara o Challenger com o Champion atual no MLflow, efetuando a promocao. |
| `make inference` | Executa o modulo de inferencia local por linha de comando para fins de homologacao rápida. |
| `make test` | Roda toda a suite de testes unitarios e de integracao utilizando pytest. |
| `make format` | Formata o codigo-fonte e organiza as importacoes utilizando a ferramenta Ruff. |
| `make clean` | Remove pastas temporarias e caches de compilacao do Python de forma multiplataforma. |

---

## Estrutura de Diretorios

```
fiap-ml-stock-price-prediction/
├── .github/workflows/          # Workflows do GitHub Actions
├── airflow/                    # Configuracao de Dags do Apache Airflow
├── deploy/                     # Dockerfiles de producao e IaC Terraform
├── docs/                       # Architecture Decision Records (ADRs) e PRD
├── src/                        # Codigo-fonte da aplicacao
│   ├── api/                    # Servico web HTTP e rotas do FastAPI
│   ├── core/                   # Configuracoes globais e logger estruturado em JSON
│   ├── domain/                 # Esquemas Pydantic para requisicoes e respostas
│   ├── infrastructure/         # Clientes de S3/MinIO e integracao com o MLflow
│   ├── ml/                     # Modelagem LSTM, features e inferencia
│   └── pipelines/              # Scripts isolados de ETL e treinamento
├── tests/                      # Suite de testes estruturados (unit e integration)
├── docker-compose.yml          # Servicos de infraestrutura local
├── Makefile                    # Interface unificada de comandos
└── pyproject.toml              # Definicao de metadados e dependencias
```

---

## Exemplos de Interacao com a API

### Verificacao de Saude (GET `/health`)
Retorna a integridade do servico, status de prontidao e o ID do modelo carregado em memoria:
```bash
curl -X 'GET' 'http://localhost:8000/health' -H 'accept: application/json'
```

Resposta:
```json
{
  "status": "ok",
  "service": "fiap-ml-stock-price-prediction",
  "version": "1.0.0",
  "model_id": "test-run-123",
  "ready": true
}
```

### Previsao de Preco (POST `/predict`)
Requisicao para obter a previsao do fechamento de amanha para um determinado ticker:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "ticker": "JNJ"
}'
```

Resposta:
```json
{
  "ticker": "JNJ",
  "predicted_return": 0.015,
  "predicted_return_std_dev": 0.002,
  "confidence_score": 95.5,
  "predicted_price_usd": 155.50,
  "prediction_date_iso": "2026-07-20",
  "prediction_model": "test-run-123"
}
```

---

## Observabilidade e Monitoramento

O servico FastAPI exporta nativamente metricas no formato do Prometheus atraves da rota `/metrics`. Configuramos alertas e paineis no Grafana para exibir:
- Metricas de Infraestrutura: Tempo de CPU, consumo de memoria, latencia de requisicoes e taxa de erro.
- Metricas de Negocio: Ultimo preco estimado predito, taxa de requisicoes por ticker e o desvio do modelo (calculado com base na variabilidade gerada pelo MC Dropout).
