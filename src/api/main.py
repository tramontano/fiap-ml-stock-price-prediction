from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.routes import router as api_router
from src.api.task_routes import router as task_router
from src.core.config import settings
from src.core.logging import APILoggingMiddleware, setup_logging
from src.infrastructure.registry import RegistryClient

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==========================================
    # FASE DE STARTUP (Boot do Contêiner)
    # ==========================================
    logger.info("Iniciando boot do contêiner. Sincronizando artefatos com o S3...")

    app.state.ready = False  # Sinaliza que ainda não está pronto para servir

    try:
        client = RegistryClient()
        model, pipeline, run_id = client.load_model()

        app.state.client = client
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
app.include_router(task_router)

Instrumentator().instrument(app).expose(app)

if __name__ == "__main__":
    # Ponto de entrada padrão para execução local ou via Dockerfile
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "local",
    )
