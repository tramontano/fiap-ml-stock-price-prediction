# Código Fonte (`src/`)

Bem-vindo ao diretório principal de código-fonte do **Stock Price Prediction**. Esta pasta contém toda a lógica da aplicação, estruturada sob os princípios de *Clean Architecture* e *MLOps*, abrangendo desde a ingestão de dados financeiros brutos até o serviço de inferência em tempo real por meio de uma API RESTful.

A arquitetura foi projetada para suportar um fluxo contínuo de experimentação e deploy, integrando ferramentas padrão de mercado como FastAPI, MLflow, Optuna e arquitetura de dados Medallion.

---

## Estrutura de Diretórios

O diretório `src/` está organizado de forma modular, garantindo a separação de responsabilidades e facilitando a manutenção e evolução do projeto.

| Diretório | Descrição Principal |
| :--- | :--- |
| `api/` | Camada de apresentação RESTful (Serving). Contém o *gateway* de entrada para inferências do modelo e verificação de saúde da aplicação. |
| `core/` | Configurações globais e utilitários transversais, como gerenciamento de variáveis de ambiente e padronização de *logs* estruturados. |
| `domain/` | Definição dos contratos de dados (Schemas Pydantic) que transitam pela API, garantindo validação e consistência. |
| `infrastructure/` | Implementação de adaptadores para serviços externos, notadamente a comunicação com *Data Lakes* (S3/MinIO) para armazenamento de dados e artefatos. |
| `ml/` | Lógica central de Machine Learning, incluindo arquitetura da rede neural LSTM, engenharia de *features*, *transformers* customizados e o orquestrador de inferência. |
| `pipelines/` | Rotinas de engenharia de dados e MLOps. Scripts executáveis para ingestão de dados, processamento Medallion, *tuning* de hiperparâmetros e promoção de modelos. |

---

## Descrição dos Módulos e Arquivos

### 1. API de Previsão (`api/`)

Responsável por expor o modelo de Machine Learning para consumo via requisições HTTP.

*   **`main.py`**: Ponto de entrada da aplicação FastAPI. Orquestra o ciclo de vida (*lifespan*) da API, encarregando-se de baixar e carregar na memória global os artefatos do modelo (modelo Keras e *pipeline* Scikit-Learn) a partir do *Storage* antes de aceitar requisições. Também configura *middlewares* de CORS e monitoramento (Prometheus).
*   **`routes.py`**: Define os *endpoints* da API.
    *   `/predict`: Rota principal que recebe um *ticker* (ex: JNJ), aciona o fluxo de inferência em tempo real e retorna a predição de preço, desvio padrão e nível de confiança.
    *   `/health`: Rota de *healthcheck* para verificar a disponibilidade do serviço.

### 2. Núcleo e Configurações (`core/`)

*   **`config.py`**: Centraliza a configuração da aplicação utilizando `pydantic_settings`. Lê variáveis do `.env` e do `pyproject.toml`, definindo constantes globais para ambiente, AWS/MinIO e URIs de rastreamento do MLflow/DagsHub. Atua como um *Singleton* importado por toda a base de código.
*   **`logging.py`**: Módulo robusto de observabilidade. Implementa um `JSONFormatter` para *logs* estruturados, *middlewares* para rastreamento de requisições (`request_id`, latência) e decoradores assíncronos (`@log_route`) para auditar o fluxo de execução de forma detalhada e padronizada.

### 3. Domínio (`domain/`)

*   **`schemas.py`**: Contém os modelos de dados baseados em Pydantic. Define o `PredictRequest` (entrada esperada pelo usuário) e o `PredictResponse` (estrutura padronizada de saída com métricas de negócio e estatísticas da previsão).

### 4. Infraestrutura (`infrastructure/`)

*   **`storage_client.py`**: Cliente de abstração para armazenamento de objetos compatível com S3 (AWS ou MinIO). Fornece métodos encapsulados para *download/upload* de artefatos de modelo e leitura/escrita de arquivos Parquet nas diferentes camadas do *Data Lake* (Bronze, Silver, Gold).

### 5. Machine Learning (`ml/`)

O coração analítico e preditivo do projeto.

*   **`inference.py`**: Módulo crítico que une os artefatos treinados aos dados novos. Possui funções para buscar o modelo "Champion" no MLflow, aplicar a engenharia de *features* em tempo real, rodar predições com *MC Dropout* (para calcular confiança e incerteza) e transformar os retornos percentuais de volta em preços em dólares (USD).
*   **`features.py`**: Utilitários para criação de janelas temporais (*sliding windows* 3D) necessárias para redes LSTM e definição do *pipeline* de *features* base.
*   **`model.py`**: Define a arquitetura topológica da rede neural profunda. Contém a função construtora `build_lstm_model` que instancia um modelo sequencial Keras com camadas LSTM, Dropout e Dense.
*   **`transformers.py`**: Classes customizadas compatíveis com Scikit-Learn (`BaseEstimator`, `TransformerMixin`) para calcular indicadores financeiros. Inclui `DailyReturnTransformer`, `EMATransformer` (Médias Móveis Exponenciais), `RSITransformer` (Índice de Força Relativa) e `FeatureSelector`.

### 6. Pipelines de Dados e MLOps (`pipelines/`)

*Scripts* desenhados para rodar de forma isolada ou orquestrados por ferramentas como Apache Airflow.

*   **`ingest_data.py`**: Etapa inicial de extração. Conecta-se à API do Yahoo Finance (`yfinance`), baixa dados históricos de ativos e os salva na camada **Bronze** do *Data Lake* em formato Parquet.
*   **`process_data.py`**: Implementa a arquitetura Medallion. Move os dados da camada Bronze para a **Silver** (limpeza de nulos e ordenação temporal) e, em seguida, aplica o *pipeline* de transformadores para gerar os indicadores financeiros (RSI, Distâncias de EMA), salvando o resultado final enriquecido na camada **Gold**.
*   **`tune_pipeline.py`**: *Script* de experimentação e treinamento. Consome a camada Gold, aplica padronização de escala (`StandardScaler`) evitando *Data Leakage*, e utiliza **Optuna** para buscar os melhores hiperparâmetros (unidades, *dropout*, taxa de aprendizado). Registra automaticamente métricas e modelos no **MLflow / DagsHub**.
*   **`promote_model.py`**: Lógica de CI/CD para modelos. Avalia as *runs* registradas no MLflow, identifica o modelo com melhor desempenho (menor RMSE) e o promove para a *tag* `Production` (Champion), sincronizando seus artefatos para o *bucket* de *Serving*.

---

## Fluxo de Operação (Resumo)

1. **Treinamento Contínuo**: Os dados fluem de `ingest_data.py` (Bronze) -> `process_data.py` (Silver/Gold) -> `tune_pipeline.py` (Treino com Optuna e MLflow) -> `promote_model.py` (Seleção do melhor modelo).
2. **Inferência em Produção**: A API FastAPI (`main.py` e `routes.py`) carrega o modelo Champion. Ao receber um *ticker*, aciona `inference.py`, que repete as etapas de ingestão e processamento apenas para a janela de tempo recente, gerando uma previsão robusta contra *Training-Serving Skew*.
