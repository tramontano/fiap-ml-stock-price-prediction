from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from prometheus_client import Counter, Gauge, Histogram

from src.core.config import settings
from src.core.logging import log_route, setup_logging
from src.domain.schemas import (
    DeleteModelRequest,
    DeleteModelResponse,
    ModelInfo,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
    PromoteModelRequest,
    PromoteModelResponse,
)
from src.ml.inference import predict

# Configura o logging
logger = setup_logging()

router = APIRouter(prefix=settings.API_V1_STR)

# Configuração de autenticação básica
security = HTTPBasic()


def verify_api_key(credentials: HTTPBasicCredentials = Depends(security)):
    """Verifica as credenciais de autenticação básica para as rotas de tarefas."""
    correct_username = settings.API_USERNAME
    correct_password = settings.API_PASSWORD

    if (
        credentials.username != correct_username
        or credentials.password != correct_password
    ):
        logger.warning(
            f"Tentativa de acesso não autorizado com usuário: {credentials.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


# --- Prometheus Setup ---
# Define um medidor para guardar o valor da última previsão de preço
model_drift = Gauge(
    "model_drift",
    "Average value of predictions made by the service",
    # registry=prometheus_registry,
)

# Contador de requisições por Ticker e Modelo
prediction_requests_total = Counter(
    "prediction_requests_total",
    "Total number of prediction requests",
    ["ticker", "model_id"],
    # registry=prometheus_registry,
)

# Histograma para medir a latência da inferência
prediction_duration_seconds = Histogram(
    "prediction_duration_seconds",
    "Time spent processing prediction",
    ["ticker"],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    # registry=prometheus_registry,
)

# Gauge para monitorar o último preço predito (útil para dashboards de monitoramento de negócio)
last_predicted_price = Gauge(
    "last_predicted_price_usd",
    "The last predicted price value in USD",
    ["ticker", "model_id"],
    # registry=prometheus_registry,
)


@log_route(logger=logger, include_args=False)
@router.get(
    "/model",
    response_model=ModelInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Retorna informações do modelo atualmente em produção (Champion) e Challenger",
    tags=["Model"],
)
async def get_model(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Retorna informações do modelo atualmente em produção (Champion) e Challenger."""
    client = request.app.state.client
    try:
        champion_run_id = client.get_champion_run_id()
        challenger_run_id = client.get_challenger_run_id()

        logger.info(f"Buscando informações do modelo Champion: {champion_run_id}")
        champion_metrics = None
        if champion_run_id:
            champion_metrics = client.get_run_metrics(champion_run_id)

        logger.info(f"Buscando informações do modelo Challenger: {challenger_run_id}")
        challenger_metrics = None
        if challenger_run_id:
            challenger_metrics = client.get_run_metrics(challenger_run_id)

        return ModelInfoResponse(
            champion=ModelInfo(
                run_id=champion_run_id,
                stage="champion",
                metrics=champion_metrics,
                trained_at=client.get_model_creation_date(champion_run_id),
            )
            if champion_run_id
            else None,
            challenger=ModelInfo(
                run_id=challenger_run_id,
                stage="challenger",
                metrics=challenger_metrics,
                trained_at=client.get_model_creation_date(challenger_run_id),
            )
            if challenger_run_id
            else None,
        )
    except Exception as e:
        logger.error(f"Erro ao buscar informações do modelo: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@log_route(logger=logger, include_args=False)
@router.patch(
    "/model",
    response_model=PromoteModelRequest,
    status_code=status.HTTP_200_OK,
    summary="Promove o modelo Challenger para Champion",
    tags=["Model"],
)
async def promote_model(
    request: Request,
    payload: PromoteModelRequest = Body(None),
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Promove o modelo Challenger para Champion."""
    client = request.app.state.client
    try:
        previous_champion_run_id = client.get_champion_run_id()

        if not payload.run_id:
            promoted_run_id = client.get_challenger_run_id()
            if not promoted_run_id:
                raise ValueError("Challenger Run ID não encontrado")
        else:
            promoted_run_id = client.promote_to_champion(payload.run_id)

        client.sync_stage_to_s3("champion")
        client.sync_stage_to_s3("challenger")

        new_challenger_run_id = client.tag_challenger()

        (
            request.app.state.model,
            request.app.state.pipeline,
            request.app.state.run_id,
        ) = client.load_model()

        return PromoteModelResponse(
            promoted_run_id=promoted_run_id,
            previous_champion_run_id=previous_champion_run_id,
            new_challenger_run_id=new_challenger_run_id,
        )
    except Exception as e:
        logger.error(f"Erro ao promover o modelo: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@log_route(logger=logger, include_args=False)
@router.delete(
    "/model",
    response_model=DeleteModelRequest,
    status_code=status.HTTP_200_OK,
    summary="Deleta o modelo",
    tags=["Model"],
)
async def delete_model(
    request: Request,
    payload: DeleteModelRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Deleta o modelo"""
    client = request.app.state.client
    try:
        response = client.delete_run(payload.run_id)

        return DeleteModelResponse(
            run_id=payload.run_id,
            removed=response,
        )
    except Exception as e:
        logger.error(f"Erro ao deletar o modelo: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@log_route(logger=logger, include_args=True)
@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Realiza a previsão do próximo preço de fecho usando a rede LSTM",
    tags=["Model"],
)
async def predict_stock(payload: PredictRequest, request: Request):
    """Recebe um Ticker, busca os dados recentes e prevê o preço de amanhã."""

    # Puxa os modelos da memória do app
    model = getattr(request.app.state, "model", None)
    pipeline = getattr(request.app.state, "pipeline", None)
    run_id = getattr(request.app.state, "run_id", None)

    logger.info(
        f"Estado de memoria: model={model}, pipeline={pipeline}, run_id={run_id}"
    )

    if model is None or pipeline is None:
        logger.error(
            "Tentativa de inferência com a API desalinhada. Artefatos ausentes."
        )
        raise HTTPException(
            status_code=503,
            detail="O modelo de Machine Learning ou o Scaler ainda não estão disponíveis na memória.",
        )

    try:
        result = predict(
            ticker=payload.ticker,
            time_steps=20,
            model=model,
            scaler=pipeline,
            run_id=run_id,
        )
        # Saída bruta do modelo (Return_Close)
        predicted_return = float(result["return_pred"][-1])
        # Desvio padrão das previsões de retorno
        predicted_return_std_dev = float(result["return_std_dev"][-1])
        # Nível de confiança da predição (0 a 100)
        confidence_score = float(result["confidence_score"][-1])
        model_drift.set(100 - confidence_score) if payload.ticker == "JNJ" else None
        # Preço de fechamento pós-processado (em USD)
        predicted_price_usd = float(result["price_pred"][-1])
        # Data prevista no formato ISO 8601 (YYYY-MM-DD)
        prediction_date_iso = result["dates"][-1].isoformat()
        # Rastreabilidade de qual modelo gerou o resultado
        prediction_model = str(result["model_id"])

        return PredictResponse(
            ticker=payload.ticker,
            predicted_return=predicted_return,
            predicted_return_std_dev=predicted_return_std_dev,
            confidence_score=confidence_score,
            predicted_price_usd=predicted_price_usd,
            prediction_date_iso=prediction_date_iso,
            prediction_model=prediction_model,
        )

    except Exception as e:
        logger.error(f"Erro ao processar predição: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@log_route(logger=logger, include_args=True)
@router.get("/health")
async def health_check(request: Request):
    """Verifica o status da API e retorna informações básicas.
    Returns:
        JSONResponse: Status da API, nome do serviço e versão.
    """
    payload = {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "model_id": getattr(request.app.state, "run_id", None),
        "ready": True if getattr(request.app.state, "ready", None) else False,
    }
    return JSONResponse(status_code=200, content=payload)
