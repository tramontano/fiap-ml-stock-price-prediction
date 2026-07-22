"""
FastAPI Routes para Orquestração de Pipelines via Apache Airflow

Estas rotas permitem disparar e monitorar DAG Runs (Ingest, Process, Train,
Full Pipeline e Model Sync) no Apache Airflow usando a REST API estável (v1).
As execuções disparadas aparecem na GUI do Airflow com status em tempo real.
"""

from fastapi import APIRouter, HTTPException, Query, status
import httpx

from src.core.config import settings
from src.core.logging import log_route, setup_logging
from src.domain.schemas import (
    FullPipelineRequest,
    IngestRequest,
    ProcessRequest,
    TrainRequest,
    DAGRunTriggerResponse,
    DAGRunStatusResponse,
    TaskInstanceDetail,
)

logger = setup_logging()

router = APIRouter(prefix=settings.API_V1_STR, tags=["Pipeline"])

# Autenticação Basic Auth reutilizada em todas as chamadas ao Airflow
_airflow_auth = httpx.BasicAuth(settings.AIRFLOW_USERNAME, settings.AIRFLOW_PASSWORD)


async def trigger_dag_run(
    dag_id: str, conf: dict
) -> DAGRunTriggerResponse:
    """Dispara uma DAG Run no Apache Airflow via REST API.

    Args:
        dag_id: Identificador da DAG no Airflow (ex: 'ml_full_pipeline').
        conf: Dicionário de configuração passado via dag_run.conf para as tasks.

    Returns:
        DAGRunTriggerResponse com os dados da DAG Run criada.

    Raises:
        HTTPException: Se o Airflow retornar erro ou estiver indisponível.
    """
    url = f"{settings.AIRFLOW_API_URL}/api/v2/dags/{dag_id}/dagRuns"
    body = {"conf": conf}

    logger.info(
        f"Disparando DAG Run: dag_id={dag_id} via Airflow REST API em {url} "
        f"com conf={conf}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                url, json=body, auth=_airflow_auth
            )

            if response.status_code not in (200, 201):
                logger.error(
                    f"Falha ao disparar DAG Run: Airflow retornou status "
                    f"{response.status_code}. Response: {response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Airflow retornou erro: {response.text}",
                )

            data = response.json()
            return DAGRunTriggerResponse(
                dag_id=data["dag_id"],
                dag_run_id=data["dag_run_id"],
                logical_date=data.get("logical_date", data.get("execution_date", "")),
                state=data["state"],
            )

        except httpx.RequestError as exc:
            logger.error(f"Erro ao conectar com o Apache Airflow: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar ao Apache Airflow: {exc}",
            )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/ingest",
    response_model=DAGRunTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara o pipeline de dados (Ingestão + Processamento)",
)
async def trigger_ingest(payload: IngestRequest):
    """Extrai dados financeiros do Yahoo Finance (Bronze) e processa features (Gold).

    Dispara a DAG `ml_data_pipeline` no Airflow, que executa:
    1. Ingestão de dados via yfinance → MinIO (Bronze)
    2. Feature Engineering → MinIO (Gold)
    """
    return await trigger_dag_run(
        dag_id="ml_data_pipeline",
        conf={
            "ticker": payload.ticker,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
        },
    )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/process",
    response_model=DAGRunTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara o pipeline de dados a partir de dados existentes",
)
async def trigger_process(payload: ProcessRequest):
    """Lê dados brutos existentes da camada Bronze e gera features na camada Gold.

    Dispara a DAG `ml_data_pipeline` no Airflow passando ticker e parquet_name
    para que a task de processamento localize o arquivo correto.
    """
    return await trigger_dag_run(
        dag_id="ml_data_pipeline",
        conf={
            "ticker": payload.ticker,
            "parquet_name": payload.parquet_name,
        },
    )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/train",
    response_model=DAGRunTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara o treinamento do modelo LSTM",
)
async def trigger_train(payload: TrainRequest):
    """Treina o modelo LSTM usando dados da camada Gold e salva no Model Registry.

    Dispara a DAG `ml_train_only` no Airflow.
    """
    return await trigger_dag_run(
        dag_id="ml_train_only",
        conf={
            "params": payload.params,
        },
    )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/full",
    response_model=DAGRunTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara o pipeline completo (Ingestão → Processamento → Treinamento)",
)
async def trigger_full(payload: FullPipelineRequest):
    """Executa a sequência completa de ponta a ponta: Ingestão, Processamento e Treinamento.

    Dispara a DAG `ml_full_pipeline` no Airflow.
    """
    return await trigger_dag_run(
        dag_id="ml_full_pipeline",
        conf={
            "ticker": payload.ticker,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "params": payload.params,
        },
    )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/sync_model",
    response_model=DAGRunTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara a sincronização do modelo Champion para o S3",
)
async def trigger_sync_model():
    """Baixa o pointer JSON do Champion e sincroniza artefatos (feature_pipeline + lstm_model) para o S3/MinIO.

    Dispara a DAG `ml_model_sync` no Airflow.
    """
    return await trigger_dag_run(
        dag_id="ml_model_sync",
        conf={},
    )


@log_route(logger=logger, include_args=False)
@router.get(
    "/pipeline/status/{dag_run_id}",
    response_model=DAGRunStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta o estado detalhado de uma DAG Run",
)
async def get_pipeline_status(
    dag_run_id: str,
    dag_id: str = Query(
        ...,
        description="Identificador da DAG no Airflow (ex: 'ml_full_pipeline').",
    ),
):
    """Obtém o estado geral e o status de cada task de uma DAG Run específica.

    Requer o `dag_id` como query parameter porque a Airflow REST API
    organiza as DAG Runs sob cada DAG.
    """
    base_url = settings.AIRFLOW_API_URL
    run_url = f"{base_url}/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}"
    tasks_url = f"{run_url}/taskInstances"

    logger.info(
        f"Consultando status da DAG Run: dag_id={dag_id}, "
        f"dag_run_id={dag_run_id}"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Busca estado da DAG Run
            run_response = await client.get(run_url, auth=_airflow_auth)

            if run_response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"DAG Run '{dag_run_id}' não encontrada "
                        f"na DAG '{dag_id}' do Airflow."
                    ),
                )
            elif run_response.status_code != 200:
                logger.error(
                    f"Falha ao consultar DAG Run: Airflow retornou status "
                    f"{run_response.status_code}. Response: {run_response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Airflow retornou erro: {run_response.text}",
                )

            run_data = run_response.json()

            # Busca task instances
            tasks_response = await client.get(tasks_url, auth=_airflow_auth)
            tasks_detail = []

            if tasks_response.status_code == 200:
                tasks_data = tasks_response.json()
                for t in tasks_data.get("task_instances", []):
                    tasks_detail.append(
                        TaskInstanceDetail(
                            task_id=t.get("task_id", "unknown"),
                            state=t.get("state"),
                            start_date=t.get("start_date"),
                            end_date=t.get("end_date"),
                            duration=t.get("duration"),
                        )
                    )

            return DAGRunStatusResponse(
                dag_id=run_data["dag_id"],
                dag_run_id=run_data["dag_run_id"],
                state=run_data["state"],
                start_date=run_data.get("start_date"),
                end_date=run_data.get("end_date"),
                tasks=tasks_detail,
            )

        except httpx.RequestError as exc:
            logger.error(f"Erro ao conectar com o Apache Airflow: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Não foi possível conectar ao Apache Airflow: {exc}",
            )
