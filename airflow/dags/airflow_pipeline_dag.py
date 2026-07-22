"""DAGs de orquestração do pipeline de ML para Apache Airflow 3.x."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

default_args = {
    'owner': 'mlops',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}


# -----------------------------------------------------------------------------
# Tarefas Compartilhadas (Python Callables)
# -----------------------------------------------------------------------------
def ingest_data_task(**kwargs):
    """Bronze: Extrai dados financeiros do Yahoo Finance e guarda no MinIO."""
    from src.pipelines.ingest_data import run_ingestion

    dag_run = kwargs.get('dag_run')
    conf = dag_run.conf if dag_run and dag_run.conf else {}
    ticker = conf.get("ticker", "JNJ")
    start_date = conf.get("start_date", "1985-01-01")
    yesterday = datetime.now() - timedelta(1)
    end_date = conf.get("end_date", yesterday.strftime('%Y-%m-%d'))

    print(f"Iniciando Ingestão: ticker={ticker}, start={start_date}, end={end_date}")
    data, parquet_name = run_ingestion(ticker, start_date, end_date)

    ti = kwargs['ti']
    ti.xcom_push(key='parquet_name', value=parquet_name)
    ti.xcom_push(key='ticker', value=ticker)

    return {"parquet_name": parquet_name, "rows": len(data), "ticker": ticker}


def process_data_task(**kwargs):
    """Silver -> Gold: Limpeza dos dados brutos e Feature Engineering."""
    from src.pipelines.process_data import run_data_processing

    ti = kwargs['ti']
    dag_run = kwargs.get('dag_run')
    conf = dag_run.conf if dag_run and dag_run.conf else {}

    parquet_name = ti.xcom_pull(task_ids='ingest_data', key='parquet_name') or conf.get(
        "parquet_name", "JNJ/19850102_20251230.parquet"
    )
    ticker = ti.xcom_pull(task_ids='ingest_data', key='ticker') or conf.get("ticker", "JNJ")

    print(f"Iniciando Processamento: ticker={ticker}, parquet={parquet_name}")
    df_silver, df_gold = run_data_processing(ticker, parquet_name)

    return {
        "parquet_name": parquet_name,
        "ticker": ticker,
        "silver_rows": len(df_silver),
        "gold_rows": len(df_gold),
    }


def train_model_task(**kwargs):
    """Treina o modelo LSTM com os parâmetros do Champion ou fornecidos na execução."""
    from src.pipelines.tune_pipeline import train

    dag_run = kwargs.get('dag_run')
    conf = dag_run.conf if dag_run and dag_run.conf else {}
    params = conf.get("params", None)

    print(f"Iniciando Treinamento: {'parâmetros customizados' if params else 'parâmetros do Champion'}")
    train(param=params)

    return {"status": "training_complete"}


def sync_model_task(**kwargs):
    """Baixa o pointer JSON do Champion e sincroniza artefatos para o S3/MinIO."""
    from src.pipelines.model_sync import sync_model

    print("Iniciando sincronização do modelo Champion para o S3...")
    success = sync_model()

    if not success:
        raise RuntimeError("Falha na sincronização do modelo Champion.")

    return {"status": "sync_complete", "success": success}


# -----------------------------------------------------------------------------
# DAG 1: Pipeline Completo (Ingest -> Process -> Train)
# -----------------------------------------------------------------------------
with DAG(
    'ml_full_pipeline',
    default_args=default_args,
    description='Full ML Pipeline (Ingest, Process, Train)',
    schedule='0 0 * * 0',
    catchup=False,
    tags=['mlops', 'pipeline_completo'],
) as dag_full:
    t1 = PythonOperator(
        task_id='ingest_data',
        python_callable=ingest_data_task,
    )
    t2 = PythonOperator(
        task_id='process_data',
        python_callable=process_data_task,
    )
    t3 = PythonOperator(
        task_id='train_model',
        python_callable=train_model_task,
    )

    t1 >> t2 >> t3


# -----------------------------------------------------------------------------
# DAG 2: Pipeline de Dados (Ingest -> Process)
# -----------------------------------------------------------------------------
with DAG(
    'ml_data_pipeline',
    default_args=default_args,
    description='Data Pipeline (Ingest, Process)',
    schedule=None,
    catchup=False,
    tags=['mlops', 'pipeline_dados'],
) as dag_data:
    t1_data = PythonOperator(
        task_id='ingest_data',
        python_callable=ingest_data_task,
    )
    t2_data = PythonOperator(
        task_id='process_data',
        python_callable=process_data_task,
    )

    t1_data >> t2_data


# -----------------------------------------------------------------------------
# DAG 3: Apenas Treinamento
# -----------------------------------------------------------------------------
with DAG(
    'ml_train_only',
    default_args=default_args,
    description='Train Model Only',
    schedule=None,
    catchup=False,
    tags=['mlops', 'pipeline_treinamento'],
) as dag_train:
    t3_train = PythonOperator(
        task_id='train_model',
        python_callable=train_model_task,
    )


# -----------------------------------------------------------------------------
# DAG 4: Sincronização do Modelo Champion para o S3
# -----------------------------------------------------------------------------
with DAG(
    'ml_model_sync',
    default_args=default_args,
    description='Sync Champion Model to S3/MinIO',
    schedule=None,
    catchup=False,
    tags=['mlops', 'model_sync'],
) as dag_sync:
    t_sync = PythonOperator(
        task_id='sync_model',
        python_callable=sync_model_task,
    )
