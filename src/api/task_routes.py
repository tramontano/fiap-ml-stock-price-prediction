"""
FastAPI Routes para Execução de Tarefas do Pipeline (Airflow Task Execution)

Estas rotas executam as funções do pipeline diretamente (sem chamar o Airflow de volta).
Cada rota corresponde a uma task do DAG e recebe dados via JSON, retornando resultados
que podem ser passados para a próxima task via XCom do Airflow.

Autenticação: Basic Auth com credenciais configuráveis via .env
"""

from datetime import datetime

import optuna
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.core.config import settings
from src.core.logging import log_route, setup_logging
from src.domain.task_schemas import (
    ExtractDataRequest,
    ExtractDataResponse,
    GetFinalParametersRequest,
    GetFinalParametersResponse,
    GetParametersRequest,
    GetParametersResponse,
    LoadDataRequest,
    LoadDataResponse,
    OptimizeParamRequest,
    OptimizeParamResponse,
    PromoteModelRequest,
    PromoteModelResponse,
    TrainNewModelRequest,
    TrainNewModelResponse,
    TransformDataRequest,
    TransformDataResponse,
)
from src.infrastructure.registry import RegistryClient
from src.pipelines.ingest_data import run_ingestion
from src.pipelines.process_data import run_data_processing
from src.pipelines.tune_pipeline import load_and_prepare_data, objective, train

logger = setup_logging()

router = APIRouter(prefix=settings.API_V1_STR, tags=["Tasks"])

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


# =============================================================================
# TASK 1: Extract Data (Bronze Layer)
# =============================================================================


@log_route(logger=logger, include_args=True)
@router.post(
    "/tasks/extract_data",
    response_model=ExtractDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Extrai dados financeiros do Yahoo Finance (Bronze)",
)
async def task_extract_data(
    payload: ExtractDataRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Executa a extração de dados financeiros via yfinance e armazena na camada Bronze.

    Recebe:
        - ticker: Símbolo da ação (ex: JNJ, AAPL)
        - start_date: Data de início (YYYY-MM-DD)
        - end_date: Data de fim (YYYY-MM-DD)

    Retorna:
        - parquet_name: Caminho do arquivo no S3/MinIO
        - rows: Número de linhas extraídas
        - ticker: Ticker processado
    """
    try:
        logger.info(
            f"Iniciando extração: ticker={payload.ticker}, start={payload.start_date}, end={payload.end_date}"
        )
        data, parquet_name = run_ingestion(
            payload.ticker, payload.start_date, payload.end_date
        )

        result = ExtractDataResponse(
            parquet_name=parquet_name,
            rows=len(data),
            ticker=payload.ticker,
        )
        logger.info(f"Extração concluída: {result}")
        return result

    except Exception as e:
        logger.error(f"Erro na task extract_data: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TASK 2: Transform Data (Silver -> Gold)
# =============================================================================


@log_route(logger=logger, include_args=True)
@router.post(
    "/tasks/transform_data",
    response_model=TransformDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Processa e engenharia de features (Silver -> Gold)",
)
async def task_transform_data(
    payload: TransformDataRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Executa limpeza de dados e feature engineering na camada Gold.

    Recebe:
        - ticker: Símbolo da ação
        - parquet_name: Caminho do arquivo Bronze

    Retorna:
        - parquet_name: Caminho do arquivo Gold
        - ticker: Ticker processado
        - silver_rows: Número de linhas na camada Silver
        - gold_rows: Número de linhas na camada Gold
    """
    try:
        logger.info(
            f"Iniciando transformação: ticker={payload.ticker}, parquet={payload.parquet_name}"
        )
        df_silver, df_gold = run_data_processing(payload.ticker, payload.parquet_name)

        result = TransformDataResponse(
            parquet_name=payload.parquet_name,
            ticker=payload.ticker,
            silver_rows=len(df_silver),
            gold_rows=len(df_gold),
        )
        logger.info(f"Transformação concluída: {result}")
        return result

    except Exception as e:
        logger.error(f"Erro na task transform_data: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TASK 3: Load Data (Preparação para Treinamento)
# =============================================================================


@log_route(logger=logger, include_args=True)
@router.post(
    "/tasks/load_data",
    response_model=LoadDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Carrega dados Gold e aplica StandardScaler",
)
async def task_load_data(
    payload: LoadDataRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Carrega dados da camada Gold e aplica normalização.

    NOTA: Os arrays NumPy (X_train, y_train, etc.) não são serializáveis em JSON.
    Por isso, esta task retorna apenas metadados. O Airflow precisa armazenar
    os arrays em cache local ou usar um serviço de cache (Redis/Memcached).

    Recebe:
        - parquet_name: Caminho do arquivo Gold

    Retorna:
        - parquet_name: Confirmação do arquivo processado
        - status: "loaded" (indica que os dados foram carregados com sucesso)
        - X_train_shape, y_train_shape, X_val_shape, y_val_shape: Shapes dos arrays
    """
    try:
        logger.info(f"Carregando dados: parquet={payload.parquet_name}")
        X_train, y_train, X_val, y_val, fitted_pipeline = load_and_prepare_data(
            parquet_name=payload.parquet_name
        )

        result = LoadDataResponse(
            parquet_name=payload.parquet_name,
            status="loaded",
            X_train_shape=X_train.shape,
            y_train_shape=y_train.shape,
            X_val_shape=X_val.shape,
            y_val_shape=y_val.shape,
        )
        logger.info(f"Dados carregados: {result}")
        return result

    except Exception as e:
        logger.error(f"Erro na task load_data: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TASK 4: Get Parameters (Coleta de Hiperparâmetros)
# =============================================================================


@log_route(logger=logger, include_args=True)
@router.post(
    "/tasks/get_parameters",
    response_model=GetParametersResponse,
    status_code=status.HTTP_200_OK,
    summary="Coleta parâmetros do Champion ou usa fornecidos",
)
async def task_get_parameters(
    payload: GetParametersRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Coleta e prepara parâmetros para treinamento.

    Se train_parameters estiver vazio, busca os parâmetros do modelo Champion.
    Caso contrário, usa os fornecidos.

    Recebe:
        - train_parameters: Dict com parâmetros customizados (opcional)

    Retorna:
        - Dict com os parâmetros finais (units, dropout_rate, learning_rate, etc.)
    """
    try:
        if not payload.train_parameters or payload.train_parameters == {}:
            logger.info("Buscando parâmetros do modelo Champion...")
            client = RegistryClient()
            run_id = client.get_champion_run_id()
            champ_param = client.get_run_params(run_id)
            param = GetParametersResponse(
                units=champ_param.get("units", 128),
                dropout_rate=champ_param.get("dropout_rate", 0.22418282771976486),
                learning_rate=champ_param.get("learning_rate", 0.00014377259),
                batch_size=champ_param.get("batch_size", 64),
                activation=champ_param.get("activation", "relu"),
                epochs=champ_param.get("epochs", 75),
            )
        else:
            logger.info("Usando parâmetros fornecidos")
            param = GetParametersResponse(
                units=payload.train_parameters.get("units", 128),
                dropout_rate=payload.train_parameters.get(
                    "dropout_rate", 0.22418282771976486
                ),
                learning_rate=payload.train_parameters.get(
                    "learning_rate", 0.00014377259
                ),
                batch_size=payload.train_parameters.get("batch_size", 64),
                activation=payload.train_parameters.get("activation", "relu"),
                epochs=payload.train_parameters.get("epochs", 75),
            )

        logger.info(f"Parâmetros finais: {param}")
        return param

    except Exception as e:
        logger.error(f"Erro na task get_parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TASK 5: Optimize Parameters (Optuna Hyperparameter Tuning)
# =============================================================================


@log_route(logger=logger, include_args=True)
@router.post(
    "/tasks/optimize_param",
    response_model=OptimizeParamResponse,
    status_code=status.HTTP_200_OK,
    summary="Executa otimização de hiperparâmetros com Optuna",
)
async def task_optimize_param(
    payload: OptimizeParamRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Executa o Optuna para encontrar os melhores hiperparâmetros.

    NOTA: Esta task é computacionalmente intensiva. Requer que os dados
    (X_train, y_train, X_val, y_val, fitted_pipeline) estejam disponíveis.
    No Airflow, esses dados podem ser armazenados em cache local ou em um
    serviço de cache compartilhado.

    Recebe:
        - parquet_name: Caminho do arquivo Gold (para recarregar dados se necessário)

    Retorna:
        - run_id: ID da run pai no MLflow
        - best_params: Dict com os melhores parâmetros encontrados
    """
    try:
        logger.info(f"Iniciando otimização de parâmetros para: {payload.parquet_name}")

        # Recarrega os dados
        X_train, y_train, X_val, y_val, fitted_pipeline = load_and_prepare_data(
            parquet_name=payload.parquet_name
        )

        client = RegistryClient()
        # Iniciamos uma "run" pai no MLflow para agrupar todas as tentativas do Optuna
        with client.start_run(
            run_name=datetime.now().strftime("%Y%m%d_%H%M%S")
        ) as parent_run:
            run_id = parent_run.info.run_id
            # 3. Cria o estudo do Optuna
            study = optuna.create_study(
                direction="minimize",
                study_name="lstm_tuning",
                load_if_exists=True,
            )

            # Executa N tentativas (trials)
            n_trials = 3
            logger.info(
                f"Iniciando o Optuna ({n_trials} tentativas). Pode demorar alguns minutos..."
            )
            study.optimize(
                lambda trial: objective(
                    trial, X_train, y_train, X_val, y_val, fitted_pipeline
                ),
                n_trials=n_trials,
                n_jobs=-1,
            )
        client.end_run()

        logger.info("\nOtimização concluída!")
        logger.info(f"Melhores hiperparâmetros encontrados: {study.best_params}")
        logger.info(f"Menor RMSE atingido: {study.best_value}")

        # Regista os melhores parâmetros na run pai
        client.log_params({"best_" + k: v for k, v in study.best_params.items()})

        result = OptimizeParamResponse(
            run_id=run_id,
            best_params=study.best_params,
        )
        logger.info(f"Otimização concluída: {result}")
        return result

    except Exception as e:
        logger.error(f"Erro na task optimize_param: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TASK 6: Get Final Parameters (Decisão de Parâmetros)
# =============================================================================


@log_route(logger=logger, include_args=True)
@router.post(
    "/tasks/get_final_parameters",
    response_model=GetFinalParametersResponse,
    status_code=status.HTTP_200_OK,
    summary="Seleciona parâmetros finais (otimizados ou base)",
)
async def task_get_final_parameters(
    payload: GetFinalParametersRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Seleciona os parâmetros finais baseado na decisão de otimização.

    Recebe:
        - use_optimized: Boolean indicando se deve usar parâmetros otimizados
        - optimized_params: Dict com parâmetros otimizados (se use_optimized=True)
        - base_params: Dict com parâmetros base

    Retorna:
        - Dict com os parâmetros finais selecionados
    """
    try:
        if payload.use_optimized and payload.optimized_params:
            logger.info("Usando parâmetros otimizados")
            return GetFinalParametersResponse(**payload.optimized_params)
        else:
            logger.info("Usando parâmetros base")
            return GetFinalParametersResponse(**payload.base_params)

    except Exception as e:
        logger.error(f"Erro na task get_final_parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TASK 7: Train New Model
# =============================================================================


@log_route(logger=logger, include_args=True)
@router.post(
    "/tasks/train_new_model",
    response_model=TrainNewModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Treina um novo modelo LSTM",
)
async def task_train_new_model(
    payload: TrainNewModelRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Treina um novo modelo LSTM com os parâmetros fornecidos.

    Recebe:
        - params: Dict com os hiperparâmetros
        - parquet_name: Caminho do arquivo Gold (opcional, usa default se não fornecido)

    Retorna:
        - run_id: ID da run no MLflow
    """
    try:
        logger.info(f"Iniciando treinamento com parâmetros: {payload.params}")
        train(payload.params, payload.parquet_name)

        client = RegistryClient()
        run_id = client.tag_challenger()

        result = TrainNewModelResponse(
            run_id=run_id,
        )
        logger.info(f"Treinamento concluído: {result}")
        return result

    except Exception as e:
        logger.error(f"Erro na task train_new_model: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TASK 8: Promote Challenger
# =============================================================================


@log_route(logger=logger, include_args=True)
@router.post(
    "/tasks/promote_challenger",
    response_model=PromoteModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Promove o modelo Challenger para Champion",
)
async def task_promote_challenger(
    payload: PromoteModelRequest,
    credentials: HTTPBasicCredentials = Depends(verify_api_key),
):
    """Promove o modelo Challenger para Champion e sincroniza com S3.

    Recebe:
        - run_id: ID da run a ser promovida

    Retorna:
        - run_id: ID da run promovida
    """
    try:
        logger.info(f"Promovendo modelo: {payload.run_id}")

        client = RegistryClient()
        client.promote_to_champion(payload.run_id)
        client.sync_stage_to_s3("champion")

        result = PromoteModelResponse(
            run_id=payload.run_id,
        )
        logger.info(f"Promoção concluída: {result}")
        return result

    except Exception as e:
        logger.error(f"Erro na task promote_challenger: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
