"""
FastAPI Routes for Pipeline Orchestration via Celery Director

These routes allow triggering and monitoring workflows (Ingest, Process, Train,
and Full Pipeline) in Celery Director using HTTP REST calls.
"""

from fastapi import APIRouter, HTTPException, status
import httpx

from src.core.config import settings
from src.core.logging import log_route, setup_logging
from src.domain.schemas import (
    FullPipelineRequest,
    IngestRequest,
    ProcessRequest,
    TrainRequest,
    WorkflowStatusResponse,
    WorkflowTriggerResponse,
    TaskStatusDetail,
)

logger = setup_logging()

router = APIRouter(prefix=settings.API_V1_STR, tags=["Pipeline"])


async def trigger_workflow(
    workflow_name: str, payload_data: dict
) -> WorkflowTriggerResponse:
    """Helper to trigger a workflow on Celery Director."""
    url = f"{settings.DIRECTOR_API_URL}/api/workflows"
    body = {
        "project": "ml",
        "name": workflow_name,
        "payload": payload_data,
    }

    logger.info(f"Triggering workflow {workflow_name} via Celery Director at {url} with payload {payload_data}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=body)
            if response.status_code != 201:
                logger.error(
                    f"Failed to trigger workflow: Director returned status {response.status_code}. Response: {response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Celery Director returned error: {response.text}",
                )

            data = response.json()
            return WorkflowTriggerResponse(
                workflow_id=data["id"],
                project=data["project"],
                name=data["name"],
                status=data["status"],
            )

        except httpx.RequestError as exc:
            logger.error(f"Error connecting to Celery Director: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to reach Celery Director service: {exc}",
            )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/ingest",
    response_model=WorkflowTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara o pipeline de ingestão de dados (Bronze)",
)
async def trigger_ingest(payload: IngestRequest):
    """Extrai dados financeiros do Yahoo Finance e salva no MinIO (Bronze)."""
    return await trigger_workflow(
        workflow_name="DATA_PIPELINE",  # Apenas ingest + process
        payload_data={
            "ticker": payload.ticker,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
        },
    )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/process",
    response_model=WorkflowTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara o pipeline de processamento e feature engineering",
)
async def trigger_process(payload: ProcessRequest):
    """Lê os dados brutos da camada Bronze, limpa e salva as features na camada Gold."""
    # Como a task PROCESS_DATA no DATA_PIPELINE espera o parquet_name no payload se iniciada
    # diretamente, criamos um workflow DATA_PIPELINE ou passamos o payload.
    # Mas se o usuário quiser disparar a partir de dados existentes, podemos disparar
    # a task individualmente ou usar um workflow específico. No workflows.yml,
    # DATA_PIPELINE executa INGEST_DATA + PROCESS_DATA.
    # Se o usuário disparar PROCESS diretamente, podemos enviar para o DATA_PIPELINE passando
    # o ticker e o parquet_name. A task INGEST_DATA irá rodar rapidamente ou pular se
    # os parâmetros coincidirem, ou podemos simplesmente passar o payload e deixar rodar.
    # Vamos enviar para o DATA_PIPELINE.
    return await trigger_workflow(
        workflow_name="DATA_PIPELINE",
        payload_data={
            "ticker": payload.ticker,
            "parquet_name": payload.parquet_name,
        },
    )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/train",
    response_model=WorkflowTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara o treinamento do modelo LSTM",
)
async def trigger_train(payload: TrainRequest):
    """Treina o modelo LSTM usando dados da camada Gold e salva no registro."""
    return await trigger_workflow(
        workflow_name="TRAIN_ONLY",
        payload_data={
            "params": payload.params,
        },
    )


@log_route(logger=logger, include_args=True)
@router.post(
    "/pipeline/full",
    response_model=WorkflowTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispara o pipeline completo (Ingestão → Processamento → Treinamento)",
)
async def trigger_full(payload: FullPipelineRequest):
    """Executa a sequência completa de ponta a ponta: Ingestão, Processamento e Treinamento."""
    return await trigger_workflow(
        workflow_name="FULL_PIPELINE",
        payload_data={
            "ticker": payload.ticker,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "params": payload.params,
        },
    )


@log_route(logger=logger, include_args=False)
@router.get(
    "/pipeline/status/{workflow_id}",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta o estado detalhado de um workflow",
)
async def get_pipeline_status(workflow_id: str):
    """Obtém o estado geral e o status de cada task de um workflow específico pelo ID."""
    url = f"{settings.DIRECTOR_API_URL}/api/workflows/{workflow_id}"
    logger.info(f"Querying workflow status for {workflow_id} at {url}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {workflow_id} not found in Celery Director.",
                )
            elif response.status_code != 200:
                logger.error(
                    f"Failed to query workflow: Director returned status {response.status_code}. Response: {response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Celery Director returned error: {response.text}",
                )

            data = response.json()
            tasks_detail = []
            for t in data.get("tasks", []):
                tasks_detail.append(
                    TaskStatusDetail(
                        name=t.get("key", "UNKNOWN"),
                        status=t.get("status", "pending"),
                    )
                )

            return WorkflowStatusResponse(
                workflow_id=data["id"],
                status=data["status"],
                tasks=tasks_detail,
            )

        except httpx.RequestError as exc:
            logger.error(f"Error connecting to Celery Director: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to reach Celery Director service: {exc}",
            )
