import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# =============================================================================
# Configurações Padrão da DAG
# =============================================================================
default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# =============================================================================
# Definição da DAG
# =============================================================================
with DAG(
    dag_id='lstm_retrain_pipeline',
    default_args=default_args,
    description='Pipeline completo de ingestão, processamento e retreino do modelo LSTM',
    schedule_interval='0 0 * * 0', # Roda todos os domingos à meia-noite
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['mlops', 'lstm', 'finance'],
) as dag:

    # Diretório raiz do projeto (assumindo que o worker do Airflow tem acesso ao código)
    # Ajuste o PROJECT_ROOT conforme o volume montado no docker-compose do Airflow
    PROJECT_ROOT = os.getenv('AIRFLOW_PROJECT_ROOT', '/opt/airflow/project')

    # Comando base usando 'uv' (ou apenas 'python' dependendo de como o worker foi construído)
    BASE_CMD = f"cd {PROJECT_ROOT} && uv run python -m"

    # ─────────────────────────────────────────────────────────────────────────
    # Tarefa 1: Ingestão de Dados (Bronze/Silver)
    # ─────────────────────────────────────────────────────────────────────────
    ingest_task = BashOperator(
        task_id='ingest_historical_data',
        bash_command=f"{BASE_CMD} src.pipelines.ingest_data",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tarefa 2: Processamento e Feature Engineering (Gold)
    # ─────────────────────────────────────────────────────────────────────────
    process_task = BashOperator(
        task_id='process_features',
        bash_command=f"{BASE_CMD} src.pipelines.process_data",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tarefa 3: Otimização e Treino (MLflow)
    # ─────────────────────────────────────────────────────────────────────────
    tune_task = BashOperator(
        task_id='tune_and_train_lstm',
        bash_command=f"{BASE_CMD} src.pipelines.tune_pipeline",
        # Dá um timeout maior se o treino demorar muito
        execution_timeout=timedelta(hours=4),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tarefa 4: Avaliação e Promoção do Modelo (Champion)
    # ─────────────────────────────────────────────────────────────────────────
    promote_task = BashOperator(
        task_id='promote_champion_model',
        bash_command=f"{BASE_CMD} src.pipelines.promote_model",
    )

    # =========================================================================
    # Orquestração (Definição de Dependências do Grafo)
    # =========================================================================
    # O pipeline só avança se a tarefa anterior terminar com sucesso
    ingest_task >> process_task >> tune_task >> promote_task
