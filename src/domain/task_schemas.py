"""
Schemas Pydantic para as Rotas de Tarefas do Pipeline (Task Routes)

Estes schemas definem os contratos de entrada e saída para os endpoints
de execução de tarefas do pipeline via API HTTP.
"""

from typing import Optional

from pydantic import BaseModel, Field

# =============================================================================
# TASK 1: Extract Data (Bronze Layer)
# =============================================================================


class ExtractDataRequest(BaseModel):
    """Payload para a task de extração de dados financeiros."""

    ticker: str = Field(default="JNJ", description="Símbolo da ação (ex: JNJ, AAPL)")
    start_date: str = Field(
        default="1985-01-01", description="Data de início (formato YYYY-MM-DD)"
    )
    end_date: str = Field(
        default="2025-12-31", description="Data de fim (formato YYYY-MM-DD)"
    )


class ExtractDataResponse(BaseModel):
    """Resposta da task de extração de dados."""

    parquet_name: str = Field(
        description="Caminho do arquivo Parquet no bucket Bronze (ex: JNJ/19850102_20251230.parquet)",
    )
    rows: int = Field(description="Número de linhas extraídas")
    ticker: str = Field(description="Símbolo da ação processado")


# =============================================================================
# TASK 2: Transform Data (Silver → Gold)
# =============================================================================


class TransformDataRequest(BaseModel):
    """Payload para a task de transformação de dados."""

    ticker: str = Field(default="JNJ", description="Símbolo da ação")
    parquet_name: str = Field(
        default="JNJ/19850102_20251230.parquet",
        description="Caminho do arquivo Parquet no bucket Bronze",
    )


class TransformDataResponse(BaseModel):
    """Resposta da task de transformação de dados."""

    parquet_name: str = Field(
        description="Caminho do arquivo Parquet no bucket Bronze (confirmação)"
    )
    ticker: str = Field(description="Símbolo da ação processado")
    silver_rows: int = Field(
        description="Número de linhas na camada Silver (após limpeza)"
    )
    gold_rows: int = Field(
        description="Número de linhas na camada Gold (após feature engineering)"
    )


# =============================================================================
# TASK 3: Load Data (Preparação para Treinamento)
# =============================================================================


class LoadDataRequest(BaseModel):
    """Payload para a task de carregamento de dados."""

    parquet_name: str = Field(
        default="JNJ/19850102_20251230.parquet",
        description="Caminho do arquivo Parquet no bucket Gold",
    )


class LoadDataResponse(BaseModel):
    """Resposta da task de carregamento de dados.

    Nota: Os arrays NumPy (X_train, y_train, etc.) não são serializáveis em JSON.
    Esta resposta contém apenas metadados sobre os dados carregados.
    """

    parquet_name: str = Field(description="Caminho do arquivo Parquet processado")
    status: str = Field(description="Status do carregamento (ex: 'loaded')")
    X_train_shape: tuple = Field(
        description="Shape do array X_train (ex: [7960, 20, 6])"
    )
    y_train_shape: tuple = Field(description="Shape do array y_train (ex: [7960])")
    X_val_shape: tuple = Field(description="Shape do array X_val (ex: [1990, 20, 6])")
    y_val_shape: tuple = Field(description="Shape do array y_val (ex: [1990])")


# =============================================================================
# TASK 4: Get Parameters (Coleta de Hiperparâmetros)
# =============================================================================


class GetParametersRequest(BaseModel):
    """Payload para a task de coleta de parâmetros."""

    train_parameters: Optional[dict] = Field(
        default={
            "units": 128,
            "dropout_rate": 0.22418282771976486,
            "learning_rate": 0.00014377259,
            "batch_size": 64,
            "activation": "relu",
            "epochs": 75,
        },
        description="Dicionário com parâmetros customizados. Se vazio, usa os do Champion.",
    )


class GetParametersResponse(BaseModel):
    """Resposta da task de coleta de parâmetros."""

    units: int = Field(description="Número de unidades LSTM")
    dropout_rate: float = Field(description="Taxa de dropout (0.0 a 1.0)")
    learning_rate: float = Field(description="Taxa de aprendizado")
    batch_size: int = Field(description="Tamanho do batch para treinamento")
    activation: str = Field(
        description="Função de ativação (ex: 'relu', 'tanh', 'leaky_relu', 'elu')"
    )
    epochs: int = Field(description="Número de épocas de treinamento")


# =============================================================================
# TASK 5: Optimize Parameters (Optuna Hyperparameter Tuning)
# =============================================================================


class OptimizeParamRequest(BaseModel):
    """Payload para a task de otimização de parâmetros."""

    parquet_name: str = Field(
        default="JNJ/19850102_20251230.parquet",
        description="Caminho do arquivo Parquet no bucket Gold",
    )


class OptimizeParamResponse(BaseModel):
    """Resposta da task de otimização de parâmetros."""

    run_id: str = Field(
        description="ID da run pai no MLflow que agrupa todas as tentativas do Optuna",
    )
    best_params: dict = Field(
        description="Dicionário com os melhores hiperparâmetros encontrados"
    )


# =============================================================================
# TASK 6: Get Final Parameters (Decisão de Parâmetros)
# =============================================================================


class GetFinalParametersRequest(BaseModel):
    """Payload para a task de seleção de parâmetros finais."""

    use_optimized: bool = Field(
        deault=True,
        description="Se True, usa parâmetros otimizados. Se False, usa base_params.",
    )
    optimized_params: Optional[dict] = Field(
        default={},
        description="Dicionário com parâmetros otimizados (se use_optimized=True)",
    )
    base_params: Optional[dict] = Field(
        default={
            "units": 128,
            "dropout_rate": 0.22418282771976486,
            "learning_rate": 0.00014377259,
            "batch_size": 64,
            "activation": "relu",
            "epochs": 75,
        },
        description="Dicionário com parâmetros base",
    )


class GetFinalParametersResponse(BaseModel):
    """Resposta da task de seleção de parâmetros finais."""

    units: int = Field(description="Número de unidades LSTM")
    dropout_rate: float = Field(description="Taxa de dropout")
    learning_rate: float = Field(description="Taxa de aprendizado")
    batch_size: int = Field(description="Tamanho do batch")
    activation: str = Field(description="Função de ativação")
    epochs: int = Field(description="Número de épocas")


# =============================================================================
# TASK 7: Train New Model
# =============================================================================


class TrainNewModelRequest(BaseModel):
    """Payload para a task de treinamento do modelo."""

    params: dict = Field(
        default={
            "units": 128,
            "dropout_rate": 0.22418282771976486,
            "learning_rate": 0.00014377259,
            "batch_size": 64,
            "activation": "relu",
            "epochs": 75,
        },
        description="Dicionário com os hiperparâmetros para treinamento",
    )
    parquet_name: Optional[str] = Field(
        default="JNJ/19850102_20251230.parquet",
        description="Caminho do arquivo Parquet no bucket Gold (opcional, usa default se não fornecido)",
    )


class TrainNewModelResponse(BaseModel):
    """Resposta da task de treinamento do modelo."""

    run_id: str = Field(
        default="e90f4a857251476ea263723651309caa",
        description="ID da run no MLflow onde o modelo foi treinado e registrado como Challenger",
    )


# =============================================================================
# TASK 8: Promote Challenger
# =============================================================================


class PromoteModelRequest(BaseModel):
    """Payload para a task de promoção do modelo."""

    run_id: str = Field(
        default="c924005629544d7796c577205381b99e",
        description="ID da run no MLflow a ser promovida para Champion",
    )


class PromoteModelResponse(BaseModel):
    """Resposta da task de promoção do modelo."""

    run_id: str = Field(description="ID da run que foi promovida para Champion")
