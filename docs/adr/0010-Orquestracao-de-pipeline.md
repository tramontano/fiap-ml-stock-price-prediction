# 0010. Escolha de Orquestração e Background Tasks (GitHub Actions vs Celery vs Airflow)

**Data:** 2026-06-13
**Status:** Aceite

## 1. Contexto e Problema

O projeto atual (Previsão de Ativos Financeiros com LSTM) requer a execução de tarefas fora do ciclo de vida síncrono da API FastAPI. Especificamente, precisamos de:
1. Ingestão periódica de dados históricos (Data Lake Bronze/Silver).
2. Retreino periódico do modelo LSTM com otimização Bayesiana (Optuna) para evitar degradação de performance (Model Drift).

Foram avaliadas três abordagens para orquestração e execução destas tarefas:
- **GitHub Actions:** Ferramenta de CI/CD com suporte a agendamento via *cron*.
- **Celery + Redis:** Fila de tarefas distribuídas (Message Broker) nativa do ecossistema Python.
- **Apache Airflow (MWAA / DIY ECS):** Plataforma padrão da indústria para criação de fluxos de trabalho (DAGs) complexos.

O desafio reside em equilibrar a complexidade operacional, o custo da infraestrutura AWS e a necessidade real de processamento do estágio atual do projeto.

## 2. Decisão

**Decidimos adotar o Apache Airflow como a ferramenta principal para orquestração de pipelines e *cron jobs* nesta fase do projeto.**

Adotamos o Apache Airflow pelas seguintes razões:
- O fluxo de retreino é linear (Extração -> Transformação -> Treino -> Registo).
- A implementação do Airflow é mais robusta e escalável para o fluxo de retreino do modelo.

## 3. Consequências

**Positivas:**
- Menor carga cognitiva.
- Centralização da lógica de CI/CD e orquestração de dados na mesma ferramenta.

**Negativas:**
- Apenas para pipelines lineares.
- Não é ideal para recuperar pipelines no meio de uma execução (ex: se o passo 3 de 5 falhar, é complexo reiniciar apenas do passo 3).
