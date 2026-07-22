# Orquestração de Pipelines (Apache Airflow)

Este diretório contém as DAGs (Directed Acyclic Graphs) e configurações relacionadas ao Apache Airflow. O Airflow é utilizado para orquestrar e agendar a execução periódica e manual dos pipelines de ingestão de dados, processamento e treinamento de machine learning.

---

## Estrutura de Diretórios

A pasta `airflow/` está organizada da seguinte forma:

| Diretório/Arquivo | Descrição Principal |
| :--- | :--- |
| `dags/` | Diretório onde as DAGs do Airflow são armazenadas. |
| `dags/airflow_pipeline_dag.py` | Definição principal das DAGs de orquestração do projeto. |

---

## Descrição dos Módulos

### `airflow_pipeline_dag.py`

Contém quatro DAGs construídas usando `PythonOperator` que importam diretamente as lógicas de negócio presentes no pacote `src.pipelines`. Essa abordagem mantém o código do pipeline isolado do código do orquestrador.

1. **`ml_full_pipeline`**: Orquestra a execução de ponta a ponta. Extrai os dados, processa (feature engineering) e treina o modelo LSTM. Essa DAG é agendada para executar periodicamente (todo domingo à meia-noite) e usa o XCom para trafegar metadados entre as tasks.
2. **`ml_data_pipeline`**: Foca exclusivamente em manter o Data Lake atualizado (Bronze -> Silver -> Gold) com os dados mais recentes, sem engatilhar um novo treinamento do modelo.
3. **`ml_train_only`**: Executa apenas a rotina de treinamento, utilizando os dados já presentes na camada Gold. Ideal para testar novos conjuntos de hiperparâmetros ou refazer treinamentos isolados.
4. **`ml_model_sync`**: Sincroniza os artefatos do modelo Champion para o S3/MinIO.

---

## Fluxo de Operação

1. O Airflow é inicializado via `docker-compose.yml`, subindo os serviços `webserver` e `scheduler`.
2. A pasta `/src` é mapeada como volume para dentro do container do Airflow (`PYTHONPATH=/opt/airflow/src`), de modo que o scheduler consiga importar `src.pipelines` sem a necessidade de duplicar o código.
3. O Scheduler do Airflow interpreta as DAGs contidas em `airflow/dags/` a cada *heartbeat* e as expõe na UI (na porta `8080`).
4. Quando uma DAG é acionada (seja por agendamento temporal ou via disparo manual pela UI), o `PythonOperator` correspondente executa as lógicas encapsuladas nas funções `run_ingestion`, `run_data_processing` e `train`.
