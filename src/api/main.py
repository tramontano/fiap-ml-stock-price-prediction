import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.routes import router as api_router
from src.core.config import settings
from src.core.logging import APILoggingMiddleware, setup_logging
from src.infrastructure.storage_client import StorageClient
from src.ml.inference import load_artifacts

logger = setup_logging()


# Constantes de configuração dos artefatos — centralizadas aqui para facilitar testes
_BUCKET = "models"
_MODEL_NAME = "lstm_model.keras"
_SCALER_NAME = "feature_pipeline.pkl"
_LOCAL_PATH = "models/" + settings.ENVIRONMENT

# Parâmetros de retry para downloads do S3/MinIO
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2  # segundos; espera: 2^1=2s, 2^2=4s, 2^3=8s


def _download_and_load_artifacts(
    storage: StorageClient,
    bucket: str = _BUCKET,
    model_name: str = _MODEL_NAME,
    scaler_name: str = _SCALER_NAME,
    local_path: str = _LOCAL_PATH,
) -> tuple:
    """Baixa os artefatos do S3/MinIO para disco e carrega-os na memória.

    Extrai a lógica de boot do lifespan para uma função pura e testável.
    Realiza até `_MAX_RETRIES` tentativas com backoff exponencial em caso de
    falha de rede — útil ao arrancar em paralelo com `docker compose up`.

    Args:
        storage:    Cliente S3/MinIO já instanciado.
        bucket:     Nome do bucket onde os artefatos estão guardados.
        model_name: Nome do ficheiro do modelo Keras no bucket.
        scaler_name: Nome do ficheiro do pipeline scikit-learn no bucket.
        local_path: Diretório local de destino dentro do contêiner.

    Returns:
        Tupla ``(model, pipeline, run_id)`` prontos para uso em inferência.

    Raises:
        Exception: Propaga a última exceção capturada se todas as tentativas falharem.
    """
    import time

    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info(
                f"[Tentativa {attempt}/{_MAX_RETRIES}] Baixando artefatos de s3://{bucket}/..."
            )
            storage.download(local_path, bucket, model_name)
            storage.download(local_path, bucket, scaler_name)
            model, pipeline, run_id = load_artifacts(model_path=local_path)
            logger.info("Artefatos descarregados e carregados com sucesso.")
            return model, pipeline, run_id

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    f"Falha na tentativa {attempt}/{_MAX_RETRIES}: {exc}. "
                    f"Aguardando {wait}s antes de tentar novamente..."
                )
                time.sleep(wait)
            else:
                logger.error(
                    f"Todas as {_MAX_RETRIES} tentativas falharam. Último erro: {exc}"
                )

    raise last_exc  # type: ignore[misc]


def _cleanup_artifacts(
    local_path: str = _LOCAL_PATH,
    model_name: str = _MODEL_NAME,
    scaler_name: str = _SCALER_NAME,
) -> None:
    """Remove os artefatos locais de forma segura, ficheiro a ficheiro."""
    for artifact in [model_name, scaler_name]:
        artifact_path = os.path.join(local_path, artifact)
        if os.path.isfile(artifact_path):
            os.remove(artifact_path)
            logger.info(f"Artefato removido: {artifact_path}")
    if os.path.isdir(local_path) and not os.listdir(local_path):
        os.removedirs(local_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==========================================
    # FASE DE STARTUP (Boot do Contêiner)
    # ==========================================
    logger.info("Iniciando boot do contêiner. Sincronizando artefatos com o S3...")

    app.state.ready = False  # Sinaliza que ainda não está pronto para servir

    try:
        storage = StorageClient()
        model, pipeline, run_id = _download_and_load_artifacts(storage)
        app.state.pipeline = pipeline
        app.state.model = model
        app.state.run_id = run_id
        app.state.ready = True  # Pronto para servir requisições de inferência
        logger.info(
            "Modelo e pipeline de features carregados com sucesso para a memória"
        )
    except Exception as e:
        logger.error(f"Atenção: Não foi possível carregar o modelo. Erro: {e}")
        raise e

    logger.info("API pronta para receber requisições de inferência.")

    yield  # A API fica rodando e servindo requisições aqui

    # ==========================================
    # FASE DE SHUTDOWN
    # ==========================================
    logger.info("Encerrando a API. Limpando memória...")
    app.state.pipeline = None
    app.state.model = None
    app.state.run_id = None
    app.state.ready = False
    _cleanup_artifacts()


# Instanciação da aplicação atrelando o ciclo de vida
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan,
)

# Adiciona CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if settings.ENVIRONMENT == "local"
    else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(APILoggingMiddleware, logger=logger)

app.include_router(api_router)

Instrumentator().instrument(app).expose(app)

if __name__ == "__main__":
    # Ponto de entrada padrão para execução local ou via Dockerfile
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "local",
    )
