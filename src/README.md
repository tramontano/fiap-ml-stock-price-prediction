# Código Fonte (`src/`)

Bem-vindo ao diretório principal de código-fonte do **Stock Price Prediction**. Esta pasta contém toda a lógica da aplicação, estruturada sob os princípios de *Clean Architecture* e *MLOps*, abrangendo desde a ingestão de dados financeiros brutos até o serviço de inferência em tempo real por meio de uma API RESTful.

A arquitetura foi projetada para suportar um fluxo contínuo de experimentação e deploy, integrando ferramentas padrão de mercado como FastAPI, MLflow (via DagsHub), Optuna e arquitetura de dados Medallion.

---

## Estrutura de Diretórios

O diretório `src/` está organizado de forma modular, garantindo a separação de responsabilidades e facilitando a manutenção e evolução do projeto.

| Diretório | Descrição Principal |
| :--- | :--- |
| `api/` | Camada de apresentação RESTful (Serving). Contém o *gateway* de entrada para inferências do modelo e endpoints para execução de tarefas de MLOps. |
| `core/` | Configurações globais e utilitários transversais, como gerenciamento de variáveis de ambiente e padronização de *logs* estruturados. |
| `domain/` | Definição dos contratos de dados (Schemas Pydantic) que transitam pela API, garantindo validação e consistência tanto para inferência quanto para tarefas de MLOps. |
| `infrastructure/` | Implementação de adaptadores para serviços externos, notadamente a comunicação com *Data Lakes* (S3/MinIO) e registro de modelos (MLflow via DagsHub). |
| `ml/` | Lógica central de Machine Learning, incluindo arquitetura da rede neural LSTM, engenharia de *features*, *transformers* customizados e o orquestrador de inferência. |
| `pipelines/` | Rotinas de engenharia de dados e MLOps. Scripts executáveis para ingestão de dados, processamento Medallion, *tuning* de hiperparâmetros com Optuna e promoção de modelos. |

---

## Descrição dos Módulos e Arquivos

### 1. API de Previsão (`api/`)

Responsável por expor o modelo de Machine Learning para consumo via requisições HTTP, gerenciar o ciclo de vida do modelo e executar as tarefas do pipeline de dados e treinamento.

* **`main.py`**: Ponto de entrada da aplicação FastAPI. Orquestra o ciclo de vida (*lifespan*) da API, encarregando-se de baixar e carregar na memória global os artefatos do modelo (modelo Keras e *pipeline* Scikit-Learn) a partir do *Storage* S3 antes de aceitar requisições. Também configura *middlewares* de CORS, monitoramento (Prometheus) e roteadores.
* **`routes.py`**: Define os *endpoints* principais da API para inferência e gerenciamento de modelos (prefixo `/api/v1`).
  * `GET /health`: Rota de *healthcheck* para verificar a disponibilidade do serviço e informações da versão/modelo carregado.
  * `POST /predict`: Rota principal de inferência. Recebe um *ticker* (ex: JNJ), aciona o fluxo em tempo real e retorna a predição de preço, desvio padrão e nível de confiança (usando *MC Dropout*).
  * `GET /model`: Retorna informações dos modelos atualmente marcados como Champion e Challenger no MLflow. Requer autenticação básica.
  * `PATCH /model`: Promove o modelo Challenger (ou um `run_id` específico) para Champion. Requer autenticação básica.
  * `DELETE /model`: Remove um modelo do MLflow através do `run_id`. Requer autenticação básica.
* **`task_routes.py`**: Define os *endpoints* para execução isolada de tarefas do pipeline de MLOps, projetados para serem orquestrados pelo Apache Airflow (prefixo `/api/v1/tasks/`). Todas as rotas exigem autenticação básica configurável via `.env`.
  * `POST /extract_data`: Extrai dados financeiros via `yfinance` e salva na camada Bronze.
  * `POST /transform_data`: Processa os dados da camada Bronze, aplica feature engineering e salva nas camadas Silver e Gold.
  * `POST /load_data`: Carrega dados da camada Gold e aplica padronização (preparação para treino).
  * `POST /get_parameters`: Coleta os hiperparâmetros do modelo Champion atual ou usa os fornecidos no payload.
  * `POST /optimize_param`: Executa o Optuna para encontrar os melhores hiperparâmetros de treinamento.
  * `POST /get_final_parameters`: Seleciona entre os parâmetros otimizados ou os parâmetros base.
  * `POST /train_new_model`: Treina um novo modelo LSTM e o registra no MLflow como Challenger.
  * `POST /promote_challenger`: Promove um modelo específico para Champion e sincroniza os artefatos com o S3.

### 2. Núcleo e Configurações (`core/`)

* **`config.py`**: Centraliza a configuração da aplicação utilizando `pydantic_settings`. Lê variáveis do `.env` e do `pyproject.toml`, definindo constantes globais para ambiente, AWS/MinIO e URIs de rastreamento do MLflow/DagsHub. Atua como um *Singleton* importado por toda a base de código.
* **`logging.py`**: Módulo robusto de observabilidade. Implementa um `JSONFormatter` para *logs* estruturados, *middlewares* para rastreamento de requisições (`request_id`, latência) e decoradores assíncronos (`@log_route`) para auditar o fluxo de execução de forma detalhada e padronizada.

### 3. Domínio (`domain/`)

* **`schemas.py`**: Contém os modelos de dados baseados em Pydantic para as rotas principais. Define o `PredictRequest` (entrada esperada pelo usuário) e o `PredictResponse` (estrutura padronizada de saída com métricas de negócio e estatísticas da previsão), além de esquemas para gerenciamento de modelos e gatilhos de DAGs do Airflow.
* **`task_schemas.py`**: Define os contratos Pydantic específicos usados por `api/task_routes.py` para as 8 tarefas expostas via HTTP (extração, transformação, carregamento, coleta de parâmetros, otimização com Optuna, escolha final de parâmetros, treino e promoção).

### 4. Infraestrutura (`infrastructure/`)

* **`storage_client.py`**: Cliente de abstração para armazenamento de objetos compatível com S3 (AWS ou MinIO). Fornece métodos encapsulados para *download/upload* de artefatos de modelo e leitura/escrita de arquivos Parquet nas diferentes camadas do *Data Lake* (Bronze, Silver, Gold).
* **`registry.py`**: Cliente de abstração para registro de modelos combinando MLflow hospedado no DagsHub e um bucket S3/MinIO para cache de artefatos. Implementa a lógica de estágios baseada em uma tag única `stage` ("Champion" ou "Challenger"). Gerencia a sincronização de artefatos criando uma estrutura de diretórios previsível (`models/runs/{run_id}/...`) e atualizando ponteiros (`models/pointers/{stage}.json`) no S3, o que otimiza o carregamento do modelo em tempo de inferência sem depender do MLflow.

### 5. Machine Learning (`ml/`)

O coração analítico e preditivo do projeto.

* **`features.py`**: Utilitários para criação de janelas temporais (*sliding windows* 3D) necessárias para redes LSTM e definição do *pipeline* de *features* base.
* **`inference.py`**: Módulo crítico que une os artefatos treinados aos dados novos. Possui funções para orquestrar a inferência de ponta a ponta: chama a ingestão e processamento, carrega modelo/scaler do S3, cria sequências, aplica o scaler e faz predição com *MC Dropout* (para calcular confiança e incerteza) e transforma os retornos percentuais de volta em preços em dólares (USD).
* **`model.py`**: Define a arquitetura topológica da rede neural profunda. Contém a função construtora `build_lstm_model` que instancia um modelo sequencial Keras com camadas LSTM, Dropout e Dense.
* **`transformers.py`**: Classes customizadas compatíveis com Scikit-Learn (`BaseEstimator`, `TransformerMixin`) para calcular indicadores financeiros. Inclui `DailyReturnTransformer`, `EMATransformer` (Médias Móveis Exponenciais), `RSITransformer` (Índice de Força Relativa) e `FeatureSelector`.

### 6. Pipelines de Dados e MLOps (`pipelines/`)

*Scripts* desenhados para rodar de forma isolada ou orquestrados por ferramentas como Apache Airflow (via `task_routes.py`).

* **`ingest_data.py`**: Etapa inicial de extração. Conecta-se à API do Yahoo Finance (`yfinance`), baixa dados históricos de ativos e os salva na camada **Bronze** do *Data Lake* em formato Parquet.
* **`process_data.py`**: Implementa a arquitetura Medallion. Move os dados da camada Bronze para a **Silver** (limpeza de nulos e ordenação temporal) e, em seguida, aplica o *pipeline* de transformadores para gerar os indicadores financeiros (RSI, Distâncias de EMA), salvando o resultado final enriquecido na camada **Gold**.
* **`tune_pipeline.py`**: *Script* de experimentação e treinamento. Consome a camada Gold, aplica padronização de escala (`StandardScaler`) evitando *Data Leakage* (aplicando apenas nos dados de treino após a divisão temporal). Utiliza **Optuna** para buscar os melhores hiperparâmetros minimizando o RMSE. Registra automaticamente métricas (RMSE, MAE, MAPE, R2) e modelos no **MLflow / DagsHub** e salva artefatos manualmente no bucket S3 `models`.
* **`promote_model.py`**: Lógica de CI/CD para modelos. Avalia as *runs* registradas no MLflow, identifica o modelo com melhor desempenho (menor RMSE) e o promove para a *tag* `Champion`, sincronizando seus artefatos para o *bucket* de *Serving*.
* **`model_sync.py`**: Script para sincronizar o modelo Champion para o S3, garantindo que os artefatos estejam disponíveis para a API de inferência.

---

## Fluxo de Operação (Resumo)

1. **Treinamento Contínuo**: Os dados fluem de `ingest_data.py` (Bronze) -> `process_data.py` (Silver/Gold) -> `tune_pipeline.py` (Treino com Optuna e registro no MLflow/S3) -> `promote_model.py` (Seleção do melhor modelo). Todo este fluxo pode ser orquestrado via endpoints em `task_routes.py`.
2. **Inferência em Produção**: A API FastAPI (`main.py` e `routes.py`) carrega o modelo Champion a partir do bucket S3. Ao receber um *ticker*, aciona `inference.py`, que repete as etapas de ingestão e processamento apenas para a janela de tempo recente, gerando uma previsão robusta com métricas de incerteza (MC Dropout) contra *Training-Serving Skew*.
