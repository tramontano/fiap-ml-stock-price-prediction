# 📋 TODO List: Tech Challenge - Stock Price Prediction

## 1. Setup e Infraestrutura Base

- [x] Inicializar repositório Git e criar estrutura de pastas (`src`, `tests`, `docs`, etc.).
- [x] Configurar o gerenciador de pacotes `uv` e inicializar o `pyproject.toml`.
- [x] Criar arquivo `Makefile` com comandos básicos (`install`, `run`, `test`).
- [x] Configurar o `docker-compose.yml` base (MinIO e PostgreSQL local).
- [x] Configurar repositório no DagsHub e obter credenciais do MLflow.
- [x] Configurar variáveis de ambiente (.env) para MLFLOW_TRACKING_URI (DagsHub) e credenciais de acesso.

## 2. Dados e Feature Engineering (Data Lake)

- [x] Desenvolver script de extração de dados com `yfinance` (`src/pipelines/ingest_data.py`).
- [x] Configurar conector do MinIO/S3 (`src/infrastructure/storage_client.py`).
- [x] Desenvolver `DailyReturnTransformer` (cálculo de variação percentual diária).
- [x] Desenvolver `MovingAverageTransformer` (médias móveis dos retornos).
- [x] Montar o Pipeline do `scikit-learn` unindo os transformadores e o `StandardScaler`.
- [x] Salvar dados de treino/teste no formato Parquet no MinIO.

## 3. Machine Learning (Treino e Otimização)

- [x] Definir a arquitetura da rede LSTM (`src/ml/model.py`).
- [x] Criar o script de hiperparametrização com Optuna (`src/pipelines/tune_pipeline.py`).
- [x] Implementar o "Pruning" (poda) no Optuna para parar treinos ineficientes precocemente.
- [x] Integrar o MLflow no script de treino para registrar parâmetros e métricas (MAE, RMSE, MAPE).
- [x] Implementar a lógica de salvar o Pipeline de Features e o Modelo LSTM vencedor como artefatos no MLflow.

## 4. Serving (API FastAPI)

- [x] Definir os schemas Pydantic de Request e Response (`src/domain/schemas.py`).
- [x] Criar a rota POST `/predict` no FastAPI (`src/api/routes.py`).
- [ ] Implementar a lógica de busca do modelo usando o alias champion via MLflow Client (garantindo a fonte única de verdade).
- [ ] Implementar a lógica da API: baixar artefatos do MLflow, transformar dados de entrada, prever e converter o retorno de volta para preço nominal.
- [ ] Adicionar logging na API indicando qual versão (run_id) do modelo está servindo a predição.
- [ ] Adicionar testes de integração para garantir que a API responde corretamente.
- [ ] Criar `Dockerfile` focado em produção para a API.

## 5. Orquestração e MLOps

- [ ] Adicionar o Apache Airflow ao `docker-compose.yml`.
- [ ] Criar a DAG do Airflow (`airflow/dags/retrain_dag.py`) para orquestrar ingestão e treino mensalmente.
- [ ] Configurar rotina básica de CI/CD (GitHub Actions) para rodar o `pytest` a cada push.
  - [ ] Rodar uv sync e pytest.
  - [ ] Executar tune_pipeline.py (opcional/cron).
  - [ ] Automatizar a marcação de tag Challenger no DagsHub após um treino bem-sucedido no branch main.
- [ ] Adicionar script/comando Makefile promote para promover um modelo Challenger para Champion via CLI/API.

## 6. Documentação e Entrega

- [ ] Preencher o `README.md` com instruções claras de como rodar o projeto localmente.
- [ ] Gravar o vídeo demonstrando a arquitetura e fazendo uma requisição na API (Requisito do Tech Challenge).

## Roadmap Futuro: Arquitetura Multimodal (Time Series + NLP)

- **Objetivo:** Enriquecer o *dataset* preditivo com Análise de Sentimento (Alternative Data).
- **Implementação:** Utilizar o modelo **FinBERT** (Hugging Face) para processar manchetes de notícias financeiras sobre o *ticker* alvo.
- **Engenharia de Dados:** * Criar um *script* diário (Airflow) para extrair notícias da API do Yahoo Finance (`yfinance.Ticker.news`).
  - Agregar o *score* de sentimento diário (-1 a 1) resolvendo conflitos de fim-de-semana (acumulação de *score* para a abertura de segunda-feira).
  - Lidar com a assimetria histórica (como as APIs gratuitas não fornecem notícias de há 20 anos, o modelo V2 deverá ser treinado numa janela temporal mais curta, ex: últimos 3 anos, focando-se em *momentum* em vez de tendências de longo prazo).
