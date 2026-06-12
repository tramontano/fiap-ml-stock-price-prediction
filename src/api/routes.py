from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, Histogram

from src.core.config import settings
from src.core.logging import log_route, setup_logging
from src.domain.schemas import PredictRequest, PredictResponse
from src.ml.inference import predict

# Configura o logging
logger = setup_logging(use_json=True)

router = APIRouter(prefix=settings.API_V1_STR, tags=["Inference"])

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


@log_route(logger=logger, include_args=True)
@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Realiza a previsão do próximo preço de fecho usando a rede LSTM",
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
    }
    return JSONResponse(status_code=200, content=payload)
