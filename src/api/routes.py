import os
from contextlib import asynccontextmanager

import mlflow
import numpy as np
import tensorflow as tf
import tensorflow.keras as keras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# Monkey Patch: Injeta a versão no Keras para o MLflow não dar erro
if not hasattr(keras, "__version__"):
    keras.__version__ = tf.__version__

# Importa o módulo de logging
from src.core.logging import APILoggingMiddleware, log_route, setup_logging
from src.domain.schemas import PredictRequest, PredictResponse
from src.pipelines.ingest_data import run_ingestion

# Configura o logging
logger = setup_logging(use_json=True)
mlflow.tensorflow.autolog()

# Carrega as variáveis de ambiente (Credenciais DagsHub)
load_dotenv(".env/mlflow.env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executado no arranque do servidor.
    Carrega o modelo do MLflow para a memória apenas UMA vez (Best Practice).
    """
    print("Iniciando a API e conectando ao Model Registry (DagsHub)...")

    # Configura a conexão ao MLflow
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))

    # Num cenário real, usaríamos o nome do modelo registado ou o Run ID vencedor
    run_id = os.getenv("BEST_RUN_ID", None)

    try:
        print(f"Baixando artefactos da Run: {run_id}")
        pipeline = mlflow.sklearn.load_model(f"runs:/{run_id}/feature_pipeline")
        model = mlflow.keras.load_model(f"runs:/{run_id}/lstm_model")

        app.state.pipeline = pipeline
        app.state.model = model
        print("Modelo carregado com sucesso para a memória")
    except Exception as e:
        print(
            f"Atenção: Não foi possível carregar o modelo. Verifique o RUN_ID. Erro: {e}"
        )
        # Para testes locais enquanto configura o MLflow, ignoramos o erro no arranque
        raise e

    yield  # O servidor fica rodando aqui


# Cria a aplicação FastAPI
app = FastAPI(
    title="Stock Price Prediction API",
    description="API de MLOps para previsão de ações usando LSTMs e Arquitetura Medalhão.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(APILoggingMiddleware, logger=logger)

# Adiciona CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@log_route(logger=logger, include_args=True)
async def index(request: Request):
    """Testa os dados recebidos na chamada API."""

    response = {
        "method": request.method,
        "url": str(request.url),
        **request.headers,
        **request.query_params,
    }
    # return JSONResponse(context.data)  # Your context data
    return JSONResponse(response)  # Your context data


@app.post("/predict", response_model=PredictResponse)
@log_route(logger=logger, include_args=True)
async def predict_stock(payload: PredictRequest, request: Request):
    """Recebe um Ticker, busca os dados recentes e prevê o preço de amanhã."""

    # Puxa os modelos da memória do app
    model = getattr(request.app.state, "model", None)
    pipeline = getattr(request.app.state, "pipeline", None)

    if model is None or pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Modelos não carregados no servidor. Verifique o MLflow.",
        )

    try:
        # 1. Ingerindo dados
        df_recent, paquet_name = run_ingestion(payload.ticker)
        last_real_price = df_recent["Close"].iloc[-1]

        # 2. Transformação (Usa o Pipeline treinado com o StandardScaler)
        features_scaled = pipeline.transform(df_recent)

        # 3. Criar a janela de 30 dias (Sliding Window) para o LSTM
        X_input = features_scaled[-30:]

        # O Keras espera formato 3D (Amostras, Passos_Temporais, Features) -> (1, 30, N_Features)
        X_input_3d = np.expand_dims(X_input, axis=0)

        # 4. Inferência (Previsão)
        # O modelo devolve um Z-Score (ex: 1.25)
        prediction_scaled = model.predict(X_input_3d)[0][0]

        # 5. O Desfazer da Escala (Inverse Transform)
        # Sabemos que o Scaler espera 5 features: ['Return_Close',
        # 'RSI_15', 'Dist_EMA_20', 'Dist_EMA_100', 'Dist_EMA_150']
        # O retorno é a primeira coluna (índice 0)
        dummy_array = np.zeros((1, 5))
        dummy_array[0, 0] = prediction_scaled

        # Carregamos o Scaler que está dentro do nosso Pipeline
        scaler = pipeline.named_steps["scaler"]

        # Desfazemos a escala
        prediction_inversed = scaler.inverse_transform(dummy_array)

        # Agora sim, extraímos o retorno percentual real (ex: 0.012 para 1.2%)
        predicted_return = float(prediction_inversed[0, 0])

        # 6. Cálculo Final do Preço
        predicted_price = float(last_real_price * (1 + predicted_return))

        return PredictResponse(
            ticker=payload.ticker,
            predicted_return=predicted_return,
            predicted_price_usd=predicted_price,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/health")
async def health_check(request: Request):
    """Endpoint para o Docker/Kubernetes saber se a API está viva."""
    model_loaded = getattr(request.app.state, "model", None) is not None
    return {"status": "healthy", "model_loaded": model_loaded}
