from pydantic import BaseModel, Field
from typing import List

class PredictRequest(BaseModel):
    """Esquema de entrada: O utilizador envia apenas o Ticker da ação."""
    ticker: str = Field(..., description="Símbolo da ação (ex: JNJ, AAPL)")

class PredictResponse(BaseModel):
    """Esquema de saída: A API devolve a previsão matemática e de negócio."""
    ticker: str
    predicted_return: float = Field(..., description="Variação percentual prevista para o próximo dia.")
    predicted_price_usd: float = Field(..., description="Preço estimado de fecho para o próximo dia.")
