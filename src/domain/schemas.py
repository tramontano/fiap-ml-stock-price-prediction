from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """Esquema de entrada: O utilizador envia apenas o Ticker da ação."""

    ticker: str = Field(..., description="Símbolo da ação (ex: JNJ, AAPL)")


class PredictResponse(BaseModel):
    """Esquema de saída: A API devolve a previsão matemática e de negócio."""

    ticker: str
    predicted_return: float = Field(
        ..., description="Variação percentual prevista para o próximo dia."
    )
    predicted_return_std_dev: float = Field(
        ...,
        description="Desvio padrão da variação percentual prevista para o próximo dia.",
    )
    confidence_score: float = Field(
        ..., description="Nível de confiança da predição (0 a 100)."
    )
    predicted_price_usd: float = Field(
        ..., description="Preço estimado de fecho para o próximo dia."
    )
    prediction_date_iso: str = Field(
        ..., description="Data prevista no formato ISO 8601 (YYYY-MM-DD)."
    )
    prediction_model: str = Field(..., description="Modelo utilizado.")


class ModelInfo(BaseModel):
    """Informações de um run de modelo marcado em um estágio (Champion ou Challenger).

    Os campos de métrica são opcionais porque dependem do que foi
    logado em `mlflow.log_metric` durante o treino -- ajuste os nomes
    ('rmse', 'mae', 'mape') no handler da rota caso suas chaves de
    métrica no MLflow sejam diferentes destas.
    """

    run_id: str = Field(..., description="ID único do run no MLflow.")
    stage: str = Field(
        ..., description="Estágio do modelo: 'champion' ou 'challenger'."
    )
    metrics: dict[str, float] = Field(
        default_factory=dict, description="Métricas do run (ex: rmse, mape)."
    )
    trained_at: str = Field(
        ...,
        description="Timestamp ISO 8601 da última atualização do stage (YYYY-MM-DDTHH:MM:SS[.ffffff][+/-HH:MM]).",
    )


class DeleteModelRequest(BaseModel):
    """Informações de um run de modelo para deletar."""

    run_id: str = Field(..., description="ID único do run no MLflow.")


class DeleteModelResponse(BaseModel):
    """Resposta que lista os modelos deletados."""

    run_id: str = Field(..., description="ID único do run deletado.")
    removed: bool = Field(..., description="True se o modelo foi deletado com sucesso.")


class ModelInfoResponse(BaseModel):
    """Resposta que lista os modelos marcados nos estágios 'champion' e 'challenger'."""

    champion: ModelInfo | None = Field(
        None,
        description="Modelo atualmente em produção (champion).",
    )
    challenger: ModelInfo | None = Field(
        None,
        description="Modelo candidato a promoção (challenger).",
    )


class PromoteModelRequest(BaseModel):
    """Body do PATCH /model.

    Se `run_id` for omitido, promove o Challenger atualmente marcado no
    registry (fluxo normal pós-validação). Se informado, realiza um
    rollback manual, promovendo diretamente o run especificado a
    Champion -- equivalente a chamar
    `RegistryClient.promote_to_champion(run_id=...)`.
    """

    run_id: str | None = Field(
        default=None,
        description="run_id para rollback manual. Omitir para promover o Challenger atual.",
    )


class PromoteModelResponse(BaseModel):
    """Resposta do PATCH /model."""

    promoted_run_id: str = Field(
        ..., description="run_id promovido a Champion nesta chamada."
    )
    previous_champion_run_id: str | None = Field(
        default=None,
        description="run_id que era Champion antes desta promoção, se havia algum.",
    )
    new_challenger_run_id: str | None = Field(
        default=None,
        description="run_id do novo Challenger, selecionado automaticamente entre os runs remanescentes após a promoção.",
    )
