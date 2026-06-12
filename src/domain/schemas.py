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
