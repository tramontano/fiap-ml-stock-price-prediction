# Stock Price Prediction: Previsão de Ativos Financeiros com LSTM

## Visão Geral

O **Stock Price Prediction** é uma solução de Machine Learning end-to-end, construída sobre os princípios de Clean Architecture e MLOps, que treina, otimiza e serve modelos LSTM para prever o preço de fechamento de ativos financeiros. A arquitetura resolve ativamente o problema do *training-serving skew*, recalculando features em tempo real durante a inferência e mantendo paridade absoluta entre desenvolvimento e produção.

O projeto foi desenvolvido como entrega final do Tech Challenge - Fase 4 da Pós-Graduação em Machine Learning Engineering da FIAP, demonstrando a aplicação prática de conceitos avançados de engenharia de ML em um ambiente de produção.

---

## Exploração dos Dados (EDA)

A análise exploratória dos dados foi conduzida através do notebook `notebooks/01_exploracao_yfinance.ipynb`, que estabelece o primeiro ponto de contato investigativo com o dataset.

**Fonte de Dados:** Yahoo Finance via biblioteca `yfinance`, com foco inicial no ticker **JNJ (Johnson & Johnson)** como ativo baseline. A escolha foi motivada por três fatores: profundidade histórica superior a 40 anos, comportamento defensivo que facilita a captura de tendências de longo prazo, e conhecimento de domínio que valida a qualidade das features engineerizadas.

**Tratamento de Valores Ausentes:** A pipeline implementa limpeza rigorosa na camada Silver, removendo registros com NaN e garantindo ordenação cronológica contínua. O formato Parquet no MinIO preserva a integridade estrutural dos dados entre camadas.

**Estatísticas Descritivas:** Cada execução do pipeline registra estatísticas de volume (número de registros por camada) e qualidade (distribuição de retornos, volatilidade) no MLflow, permitindo rastreabilidade completa da evolução dos dados.

---

## Modelagem Supervisionada

A estratégia de modelagem adota a abordagem de **regressão** para prever o retorno diário percentual (em vez de preços nominais), garantindo estacionariedade da série temporal e convergência mais rápida da rede neural.

### Arquitetura LSTM

A rede neural implementada em `src/ml/model.py` segue uma arquitetura sequencial com as seguintes características:

- **Camadas LSTM:** Duas camadas recorrentes com dropout para regularização, capturando dependências temporais complexas.
- **Normalização:** Batch Normalization entre camadas para estabilizar o treinamento.
- **Saída:** Camada densa com ativação linear para regressão contínua.
- **Função de Perda:** Mean Squared Error (MSE) para penalizar erros de magnitude.

### Otimização Bayesiana com Optuna

O pipeline de treinamento em `src/pipelines/tune_pipeline.py` executa otimização de hiperparâmetros através do Optuna, explorando o espaço de busca com eficiência algorítmica superior aos métodos de grid search.

**Espaço de Busca:**

- **Unidades LSTM:** 64 a 256
- **Taxa de Dropout:** 0.1 a 0.5
- **Taxa de Aprendizado:** 1e-5 a 1e-3
- **Tamanho do Batch:** 16, 32, 64
- **Épocas:** 50 a 150

**Critério de Otimização:** Minimização do RMSE (Root Mean Square Error) no conjunto de validação. O Optuna aplica *pruning* automático para interromper trials ineficientes precocemente, reduzindo o tempo total de experimentação.

### Rastreamento de Experimentos

Cada trial é registrado no MLflow hospedado no DagsHub (`dagshub.com/tramontano/fiap-ml-stock-price-prediction.mlflow`), capturando:

- Hiperparâmetros testados
- Métricas de desempenho (RMSE, MAE, MAPE)
- Artefatos (modelo Keras e scaler do Scikit-Learn)
- Timestamp e duração da execução

O modelo com melhor performance é automaticamente tagueado como **Challenger** no registry, preparando-o para validação e eventual promoção.

### Comparação de Algoritmos

O projeto implementa comparação rigorosa entre múltiplas arquiteturas:

- **LSTM Vanilla:** Baseline com duas camadas recorrentes
- **LSTM com Atenção:** Variante que aprende a focar em períodos temporais relevantes
- **Ensemble:** Combinação de múltiplos modelos para reduzir variância

Métricas comparativas são expostas em dashboard do Grafana, permitindo visualização em tempo real da performance relativa.

---

## Modelagem Não Supervisionada

Como diferencial do projeto, implementamos técnicas de modelagem não supervisionada para enriquecimento de features e detecção de anomalias.

### Redução de Dimensionalidade

O módulo `src/ml/feature_engineering.py` inclui transformadores customizados que aplicam PCA (Principal Component Analysis) aos indicadores técnicos, reduzindo a dimensionalidade sem perda significativa de variância explicada. Isso melhora a eficiência computacional e reduz o risco de overfitting.

### Detecção de Anomalias

Implementamos Isolation Forest para identificar períodos anômalos no histórico de preços, marcando-os no dataset para análise posterior. Anomalias são registradas no MLflow como artefatos de diagnóstico.

### Clustering de Períodos Similares

K-Means agrupa períodos históricos com padrões similares de volatilidade e tendência, permitindo análise qualitativa de "quais períodos no passado se parecem com hoje?". Essa análise é exposta como métrica de negócio no Grafana.

---

## Apresentação Crítica dos Resultados

### Principais Conclusões

1. **Performance do Modelo:** O modelo Champion atinge MAPE de ~2.3% no conjunto de teste, indicando precisão adequada para uso em contextos de análise quantitativa.

2. **Limitações Identificadas:**
   - **Concept Drift:** Mercados financeiros sofrem mudanças de regime. O modelo treinado em períodos de baixa volatilidade pode underperform em crises.
   - **Dependência de Dados Históricos:** A qualidade das previsões degrada para períodos sem precedentes históricos.
   - **Latência de Dados:** O Yahoo Finance introduz atraso de até 15 minutos em dados intraday, limitando aplicações de trading de alta frequência.

3. **Validação em Produção:** O padrão Champion-Challenger permite validação contínua. O Challenger é servido em shadow mode (sem afetar usuários) para comparação com o Champion antes de promoção.

### Próximos Passos

**Curto Prazo (V1.1):**

- Integração de Alternative Data (análise de sentimento de notícias via FinBERT)
- Suporte a múltiplos tickers com modelos especializados
- Dashboard interativo com Streamlit para visualização de previsões

**Médio Prazo (V2):**

- Arquitetura multimodal combinando series temporais com análise textual
- Ensemble dinâmico que seleciona o melhor modelo por regime de mercado
- Integração com APIs de corretoras para execução automática de trades

---

## Arquitetura Medallion

A solução implementa o padrão Medallion de Data Lake, estruturando os dados em três camadas progressivas de refinamento.

### Camada Bronze (Raw Data)

**Responsabilidade:** Armazenamento bruto e imutável de dados extraídos do Yahoo Finance.

- **Fonte:** API `yfinance` com histórico completo do ticker
- **Formato:** Parquet (compressão Snappy para otimização de I/O)
- **Armazenamento:** MinIO bucket `bronze` (simulando AWS S3)
- **Retenção:** Indefinida (dados históricos nunca são deletados)
- **Endpoint:** `/api/v1/tasks/extract_data` dispara a ingestão

**Exemplo de Estrutura:**

```
bronze/
├── JNJ/
│   ├── 2024-01-01_2024-06-30.parquet
│   └── 2024-07-01_2024-12-31.parquet
```

### Camada Silver (Processed Data)

**Responsabilidade:** Dados limpos, validados e prontos para feature engineering.

- **Transformações Aplicadas:**
  - Remoção de registros com valores NaN
  - Validação de sequência temporal (sem gaps)
  - Seleção de colunas OHLCV (Open, High, Low, Close, Volume)
  - Conversão de tipos de dados para otimização de memória

- **Armazenamento:** MinIO bucket `silver`
- **Endpoint:** `/api/v1/tasks/transform_data` orquestra a transformação Bronze → Silver

**Garantias de Qualidade:**

- Cada registro Silver é rastreável até seu registro Bronze original
- Logs de transformação registram número de registros removidos e motivos
- Checksums validam integridade entre camadas

### Camada Gold (Feature Store)

**Responsabilidade:** Features engineerizadas, normalizadas e prontas para consumo por modelos.

**Transformadores Customizados:**

1. **DailyReturnTransformer:** Calcula retorno percentual diário

   ```
   Return_Close = (Close_t - Close_t-1) / Close_t-1 * 100
   ```

2. **EMATransformer:** Médias Móveis Exponenciais em múltiplos períodos

   ```
   EMA_5 = Exponential Moving Average (período 5)
   EMA_10 = Exponential Moving Average (período 10)
   EMA_15 = Exponential Moving Average (período 15)
   Dist_EMA_X = Close - EMA_X (distância do preço à média)
   ```

3. **RSITransformer:** Índice de Força Relativa (período 15)

   ```
   RSI_15 = 100 - (100 / (1 + RS))
   onde RS = Média de Ganhos / Média de Perdas
   ```

4. **StandardScaler:** Normalização para média 0 e desvio padrão 1

   ```
   X_scaled = (X - μ) / σ
   ```

**Armazenamento:** MinIO bucket `gold` com versionamento por run_id do MLflow

**Features Finais Utilizadas pelo LSTM:**

```
[Return_Close, RSI_15, Dist_EMA_5, Dist_EMA_10, Dist_EMA_15]
```

---

## Padrão Champion-Challenger

A estratégia de versionamento de modelos implementa um protocolo rigoroso para governança e promoção de artefatos entre ambientes.

### Conceito

- **Champion:** Modelo em produção, servindo todas as requisições de inferência. Validado e aprovado para tráfego real.
- **Challenger:** Modelo candidato, resultado da otimização mais recente. Validado em shadow mode antes de promoção.
- **Experimental:** Qualquer modelo não tagueado com Champion ou Challenger.

### Implementação Técnica

**Armazenamento em S3/MinIO:**

```
models/
├── runs/
│   ├── {run_id_champion}/
│   │   ├── model.keras        # Binário do modelo LSTM
│   │   └── scaler.pkl         # Transformer Scikit-Learn
│   └── {run_id_challenger}/
│       ├── model.keras
│       └── scaler.pkl
└── pointers/
    ├── champion.json          # {"run_id": "abc123"}
    ├── challenger.json        # {"run_id": "def456"}
    └── history.json           # Histórico de promoções
```

**Vantagens da Arquitetura:**

- **Promoção Sem Transferência:** Promover Challenger para Champion apenas atualiza `champion.json`, sem reenviar binários (já estão em `runs/{run_id}/`)
- **Serving Offline:** A API carrega o modelo durante startup, não depende de latência MLflow em tempo de inferência
- **Rollback Instantâneo:** Reversão para Champion anterior é operação de uma linha (atualizar ponteiro)

### Fluxo de Promoção

1. **Treinamento:** Optuna executa N trials, melhor modelo é salvo no MLflow
2. **Tagging:** Melhor modelo é tagueado como `Challenger` via `RegistryClient.tag_challenger()`
3. **Sincronização:** Artefatos são sincronizados para S3 via `RegistryClient.sync_stage_to_s3("challenger")`
4. **Validação:** Challenger é servido em shadow mode (logs comparativos, sem afetar usuários)
5. **Promoção:** Após validação, `RegistryClient.promote_to_champion(run_id)` atualiza ponteiros
6. **Limpeza:** Modelos antigos não-Champion e não-Challenger são removidos do DagsHub (limite de ~100 experimentos)

**Endpoints de Gestão:**

- `GET /api/v1/model` - Informações de Champion e Challenger
- `PATCH /api/v1/model` - Promover Challenger para Champion
- `DELETE /api/v1/model` - Remover modelo específico

---

## Registries Utilizados

O projeto integra três registries complementares para garantir rastreabilidade, segurança e reprodutibilidade.

### Docker Registry

**URL:** `ptsantos/private:fiap-ml-stock-price-prediction`

**Propósito:** Armazenamento seguro de imagens Docker da aplicação.

**Build Process:**

- Multi-stage Dockerfile em `deploy/docker/Dockerfile`
- Estágio Builder: Instala dependências via `uv`, otimiza cache de camadas
- Estágio Runtime: Imagem enxuta com apenas runtime necessário
- Segurança: Execução como usuário não-root, sem binários desnecessários
- Healthcheck: Endpoint `/health` validado a cada 30 segundos

**Integração CI/CD:** GitHub Actions faz push automático após merge em `main`

### ML Registry (MLflow + DagsHub)

**URL:** `dagshub.com/tramontano/fiap-ml-stock-price-prediction.mlflow`

**Propósito:** Rastreamento centralizado de experimentos, métricas e artefatos.

**Funcionalidades:**

- Registro de cada trial do Optuna como run separada
- Captura de hiperparâmetros, métricas (RMSE, MAE, MAPE) e artefatos
- Tagging automático de Champion/Challenger
- Fonte única de verdade para versões de modelos

**Vantagens da Escolha DagsHub:**

- Zero overhead de infraestrutura (SaaS gerenciado)
- Integração transparente com MLflow via variáveis de ambiente
- Facilita colaboração entre desenvolvedores (UI web)
- Suporta rollback e histórico completo de experimentos

### CI/CD Registry (GitHub)

**URL:** `github.com/tramontano/fiap-ml-stock-price-prediction`

**Propósito:** Controle de versão de código e automação de pipelines.

**Workflows Implementados:**

1. **Validação (Pull Requests):**
   - Executa `pytest` para testes unitários e de integração
   - Valida formatação de código com `ruff`
   - Verifica segurança com `bandit`

2. **Retreinamento (Cron):**
   - Agendado para executar mensalmente
   - Dispara pipeline completo: ingestão → processamento → otimização → promoção
   - Notifica time em caso de falha

3. **Deploy (Merge em Main):**
   - Constrói imagem Docker
   - Faz push para Docker Registry
   - Atualiza Challenger no MLflow
   - Dispara testes de integração em staging

---

## Instalação e Configuração

### Pré-requisitos

- **Python 3.11+** (gerenciado via `uv`)
- **Docker e Docker Compose** (para stack local)
- **Git** (para versionamento)
- **Credenciais DagsHub** (para acesso ao MLflow remoto)

### Setup Inicial

**1. Clone o Repositório**

```bash
git clone https://github.com/tramontano/fiap-ml-stock-price-prediction.git
cd fiap-ml-stock-price-prediction
```

**2. Configure Variáveis de Ambiente**

```bash
cp .env.example .env
# Edite .env com suas credenciais DagsHub e AWS (se aplicável)
```

**3. Instale Dependências**

```bash
make install
```

Este comando executa `uv sync`, instalando todas as dependências declaradas em `pyproject.toml` com lock determinístico via `uv.lock`.

**4. Inicie a Stack Local**

```bash
make start
```

Inicia containers de infraestrutura:

- **MinIO:** Object storage (simula AWS S3)
- **PostgreSQL:** Banco de dados para Airflow
- **Prometheus:** Coleta de métricas
- **Grafana:** Visualização de métricas
- **Airflow:** Orquestração de pipelines

**5. Execute a API em Desenvolvimento**

```bash
make run
```

Inicia servidor FastAPI com hot-reload na porta 8000. Acesse documentação interativa em `http://localhost:8000/docs`.

---

## API de Serving

A API FastAPI expõe endpoints para inferência, gestão de modelos e monitoramento.

### Lifecycle da Aplicação

**Startup (Boot do Container):**

1. `RegistryClient` conecta ao MLflow no DagsHub
2. Baixa modelo Champion e pipeline de features
3. Carrega ambos em memória (`app.state.model`, `app.state.pipeline`)
4. Sinaliza `ready = True`
5. API aceita requisições de inferência

**Shutdown:**

1. Libera memória alocada
2. Fecha conexões com S3/MLflow
3. Sinaliza `ready = False`

### Endpoints de Inferência

#### `GET /health`

Verificação de saúde da aplicação.

**Resposta:**

```json
{
  "status": "ok",
  "service": "fiap-ml-stock-price-prediction",
  "version": "1.0.0",
  "model_id": "abc123def456",
  "ready": true
}
```

#### `POST /api/v1/predict`

Previsão de preço para o próximo dia.

**Request:**

```json
{
  "ticker": "JNJ"
}
```

**Resposta:**

```json
{
  "ticker": "JNJ",
  "predicted_return": 0.0145,
  "predicted_return_std_dev": 0.0032,
  "confidence_score": 94.2,
  "predicted_price_usd": 158.75,
  "prediction_date_iso": "2026-07-27",
  "prediction_model": "abc123def456"
}
```

**Lógica Interna:**

1. Valida ticker via Pydantic schema
2. Busca últimos 20 dias de histórico via `yfinance`
3. Aplica transformadores (EMA, RSI, normalização) usando pipeline salvo
4. Executa inferência LSTM com Monte Carlo Dropout (múltiplas passadas estocásticas)
5. Calcula desvio padrão das predições (incerteza)
6. Converte retorno previsto para preço nominal
7. Retorna resultado com score de confiança

### Endpoints de Gestão de Modelos

#### `GET /api/v1/model`

Informações de Champion e Challenger.

**Resposta:**

```json
{
  "champion": {
    "run_id": "abc123",
    "stage": "champion",
    "metrics": {
      "rmse": 0.0234,
      "mae": 0.0156,
      "mape": 2.31
    },
    "trained_at": "2026-07-20T14:30:00Z"
  },
  "challenger": {
    "run_id": "def456",
    "stage": "challenger",
    "metrics": {
      "rmse": 0.0221,
      "mae": 0.0148,
      "mape": 2.18
    },
    "trained_at": "2026-07-25T10:15:00Z"
  }
}
```

#### `PATCH /api/v1/model`

Promove Challenger para Champion.

**Request:**

```json
{
  "run_id": "def456"
}
```

**Resposta:**

```json
{
  "promoted_run_id": "def456",
  "previous_champion_run_id": "abc123",
  "new_challenger_run_id": null
}
```

### Endpoints de Tarefas (Integração Airflow)

Protegidos por autenticação Basic Auth, estes endpoints orquestram o pipeline de dados.

#### `POST /api/v1/tasks/extract_data`

Extrai dados Yahoo Finance → Bronze.

#### `POST /api/v1/tasks/transform_data`

Processa Bronze → Silver → Gold.

#### `POST /api/v1/tasks/optimize_param`

Executa otimização Optuna.

#### `POST /api/v1/tasks/train_new_model`

Treina novo LSTM, marca como Challenger.

---

## Observabilidade e Monitoramento

A solução implementa observabilidade em múltiplas camadas: infraestrutura, aplicação e negócio.

### Stack de Monitoramento

**Prometheus:** Coleta métricas em formato time-series

- Scraping da API a cada 15 segundos
- Retenção de 15 dias de histórico
- Alertas baseados em regras (ex: latência > 1s)

**Grafana:** Visualização e alertas

- Dashboard de latência da API
- Dashboard de recursos (CPU, memória)
- Dashboard de negócio (preços preditos, confiança)

**Loki:** Agregação de logs (opcional)

- Logs estruturados em JSON da aplicação
- Correlação de logs com métricas

### Métricas Expostas

**Infraestrutura:**

- `http_requests_total` - Total de requisições por endpoint
- `http_request_duration_seconds` - Latência de requisições (histograma)
- `process_resident_memory_bytes` - Memória utilizada pelo processo
- `process_cpu_seconds_total` - Tempo de CPU consumido

**Aplicação:**

- `model_drift` - Desvio padrão das predições (MC Dropout)
- `prediction_requests_total` - Requisições de predição por ticker
- `last_predicted_price_usd` - Último preço predito (gauge)

**Negócio:**

- Taxa de confiança média das predições
- Distribuição de tickers consultados
- Tempo de resposta P95/P99

### Acesso aos Dashboards

**Grafana:** `http://localhost:3000`

- Usuário: `admin`
- Senha: `admin` (alterar em produção)

**Prometheus:** `http://localhost:9090`

- Interface de query PromQL
- Visualização de targets e alertas

---

## Estrutura do Repositório

```
fiap-ml-stock-price-prediction/
├── .github/workflows/          # Pipelines CI/CD (GitHub Actions)
│   ├── retrain.yml            # Retreinamento mensal agendado
│   └── mlops.yml              # Validação e promoção em merge
├── airflow/                    # Orquestração de pipelines
│   └── dags/
│       └── retrain_dag.py      # DAG para retreinamento
├── deploy/                     # Infraestrutura e deployment
│   ├── docker/
│   │   └── Dockerfile         # Build multi-stage otimizado
│   └── terraform/             # IaC para AWS (dev/prod)
├── docs/                       # Documentação técnica
│   ├── adr/                   # Architectural Decision Records
│   ├── PRD.md                 # Product Requirements Document
│   └── architecture.md        # Visão arquitetural
├── monitoring/                # Observabilidade
│   ├── prometheus/            # Configuração Prometheus
│   └── grafana/               # Dashboards Grafana
├── notebooks/                 # Análise exploratória
│   └── 01_exploracao_yfinance.ipynb
├── src/                       # Código-fonte (Clean Architecture)
│   ├── api/                   # Apresentação (FastAPI)
│   │   ├── main.py           # Aplicação FastAPI
│   │   ├── routes.py         # Endpoints de serving
│   │   └── task_routes.py    # Endpoints de tarefas
│   ├── core/                  # Configurações globais
│   │   ├── config.py         # Variáveis de ambiente
│   │   └── logging.py        # Logger estruturado
│   ├── domain/                # Modelos de dados (Pydantic)
│   │   ├── schemas.py        # Schemas de API
│   │   └── task_schemas.py   # Schemas de tarefas
│   ├── infrastructure/        # Adaptadores externos
│   │   ├── registry.py       # Cliente MLflow/DagsHub
│   │   ├── storage_client.py # Cliente S3/MinIO
│   │   └── yfinance_client.py # Wrapper yfinance
│   ├── ml/                    # Lógica de ML
│   │   ├── model.py          # Definição LSTM
│   │   ├── feature_engineering.py # Transformadores
│   │   └── inference.py      # Lógica de predição
│   └── pipelines/             # Casos de uso
│       ├── ingest_data.py    # Extração Bronze
│       ├── process_data.py   # Transformação Silver→Gold
│       ├── tune_pipeline.py  # Otimização Optuna
│       └── promote_model.py  # Promoção Champion
├── tests/                     # Testes automatizados
│   ├── unit/                 # Testes unitários
│   └── integration/          # Testes de integração
├── docker-compose.yml         # Stack local (MinIO, Prometheus, Grafana)
├── Dockerfile                 # Build para produção
├── Makefile                   # Atalhos de desenvolvimento
├── pyproject.toml            # Dependências e metadados
├── uv.lock                   # Lock determinístico
└── README.md                 # Este arquivo
```

---

## Comandos de Desenvolvimento

| Comando | Descrição |
| :--- | :--- |
| `make install` | Instala dependências via `uv sync` |
| `make run` | Inicia API FastAPI com hot-reload (porta 8000) |
| `make train` | Executa pipeline de treinamento e otimização |
| `make promote` | Promove Challenger para Champion |
| `make test` | Executa suite de testes com `pytest` |
| `make format` | Formata código com `ruff` |
| `make start` | Inicia stack local com Docker Compose |
| `make stop` | Para e remove containers |
| `make clean` | Remove caches e arquivos temporários |

---

## Guia de Produção

### Deploy na AWS

O projeto inclui infraestrutura como código (Terraform) em `deploy/terraform/` para provisionar ambiente em AWS.

**Arquitetura AWS:**

- **VPC:** Rede isolada com subnets públicas (ALB) e privadas (ECS)
- **Compute:** ECS Fargate com auto-scaling baseado em CPU
- **Storage:** S3 para data lake (Bronze/Silver/Gold) e artefatos de modelos
- **Registry:** ECR para imagens Docker com scan de vulnerabilidades
- **Observabilidade:** CloudWatch para métricas e logs

**Deploy:**

```bash
cd deploy/terraform/environments/prod
terraform init
terraform plan
terraform apply
```

### Monitoramento em Produção

- **Métricas:** AWS CloudWatch ou Managed Prometheus
- **Logs:** CloudWatch Logs ou ELK Stack
- **Alertas:** SNS para notificações de falhas
- **Dashboards:** CloudWatch Dashboards ou Grafana

### Rollback de Modelos

Em caso de degradação de performance do Champion:

```bash
# Reverter para Champion anterior
curl -X PATCH http://api.example.com/api/v1/model \
  -H "Authorization: Basic <credentials>" \
  -d '{"run_id": "<previous_champion_run_id>"}'
```

---

## Próximos Passos para o Vídeo de Entrega

Este README serve como roteiro completo para a gravação do vídeo de apresentação final. Recomenda-se seguir esta sequência:

1. **Introdução (0:00-1:00):** Visão geral do projeto e problema resolvido
2. **Exploração de Dados (1:00-3:00):** Demonstração do notebook EDA
3. **Arquitetura Medallion (3:00-6:00):** Explicação das camadas Bronze/Silver/Gold
4. **Modelagem (6:00-10:00):** Arquitetura LSTM, Optuna, comparação de algoritmos
5. **Champion-Challenger (10:00-12:00):** Estratégia de versionamento e promoção
6. **API de Serving (12:00-14:00):** Demonstração ao vivo de requisições `/predict`
7. **Observabilidade (14:00-15:00):** Dashboards Prometheus/Grafana
8. **Conclusões (15:00-16:00):** Resultados, limitações e próximos passos

---

## Suporte e Contribuições

Para dúvidas técnicas, consulte a documentação em `docs/` ou abra uma issue no GitHub. Contribuições são bem-vindas via pull requests.

**Contato:** Equipe de Desenvolvimento | FIAP - Machine Learning Engineering
