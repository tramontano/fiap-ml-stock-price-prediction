# Arquitetura do Sistema: Previsão de Preços de Ações

## 1. Visão Geral

O projeto `fiap-ml-stock-price-prediction` é uma solução *end-to-end* de Machine Learning projetada para prever o valor de fechamento de ativos financeiros utilizando redes neurais profundas (LSTM). A arquitetura foi concebida sob os pilares de *Clean Architecture* e MLOps, garantindo alta reprodutibilidade, isolamento de responsabilidades e facilidade de transição entre o desenvolvimento local e a produção na nuvem.

## 2. Stack Tecnológico Principal

* **Linguagem & Ecossistema:** Python gerenciado via `uv` (alta performance em builds).
* **Coleta de Dados:** `yfinance` para extração de histórico financeiro.
* **Feature Engineering:** `scikit-learn` Pipelines (transformações orientadas a objetos).
* **Modelagem de ML:** Long Short-Term Memory (LSTM) e Optuna para otimização Bayesiana.
* **Serving (API):** FastAPI.
* **Rastreamento (Tracking & Registry):** MLflow hospedado no DagsHub.
* **Orquestração:** Apache Airflow.
* **Infraestrutura & Deploy:** Docker Compose (Local) simulando AWS (ECS Fargate, MinIO simulando S3, CloudWatch).

---

## 3. Arquitetura de Dados e Machine Learning

A solução resolve o problema da não-estacionariedade dos dados financeiros convertendo preços nominais em retornos diários percentuais antes da predição, operando em um pipeline robusto.

### 3.1. Camadas de Dados (Data Lake)

* **Bronze (Raw):** Dados brutos extraídos do Yahoo Finance, sem tratamento, armazenados em formato Parquet no *Object Storage* (MinIO/S3).
* **Silver (Processed):** Dados limpos, sem valores nulos ou anomalias.
* **Gold (Features):** Dados transformados pelos *Custom Transformers* (ex: Retornos Diários, Médias Móveis), prontos para consumo da rede neural.

### 3.2. Pipeline de Treinamento

1. **Ingestão:** Extração de dados da camada Bronze para Silver.
2. **Transformação:** O `scikit-learn Pipeline` calcula retornos e normaliza os dados, sendo salvo como um artefato `.pkl`.
3. **Tuning & Treinamento:** O Optuna explora o espaço de hiperparâmetros enquanto o MLflow registra métricas (MAE, RMSE, MAPE) e parâmetros.
4. **Registro:** O modelo vencedor é promovido ao *Model Registry* no DagsHub.

---

## 4. Arquitetura de Serving (API)

A API não retreina modelos nem recalcula parâmetros de normalização de forma isolada, garantindo mitigação contra *Training-Serving Skew*.

1. O FastAPI recebe os últimos dados históricos via requisição HTTP.
2. A API faz o download durante o *startup* dos artefatos mais recentes do MLflow: o Modelo LSTM e o Pipeline de Features.
3. O Pipeline de Features transforma os dados recebidos.
4. O Modelo prevê o retorno do dia seguinte.
5. A API reconverte o retorno previsto no valor nominal de fechamento e responde ao cliente.

---

## 5. Orquestração e Observabilidade

* **Retreinamento Contínuo:** O Apache Airflow possui uma DAG configurada para ser engatilhada periodicamente (ex: a cada 30 dias), orquestrando o pipeline de dados e disparando um novo treinamento para capturar novas tendências de mercado.
* **Monitoramento:** Logs da API e métricas de sistema (uso de CPU/RAM e latência de resposta) [cite: 37, 38] são unificados (via Loki/Promtail localmente ou CloudWatch na AWS), permitindo observabilidade completa da saúde do modelo em produção.
