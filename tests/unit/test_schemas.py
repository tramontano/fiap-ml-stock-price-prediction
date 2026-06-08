import pytest
from pydantic import ValidationError
from src.domain.schemas import PredictRequest, PredictResponse

def test_predict_request_valid():
    """Valida que um ticker simples é aceito."""
    req = PredictRequest(ticker="AAPL")
    assert req.ticker == "AAPL"

def test_predict_request_missing_ticker():
    """Valida que o ticker é obrigatório."""
    with pytest.raises(ValidationError):
        PredictRequest()

def test_predict_response_types():
    """Garante que a resposta converte tipos corretamente."""
    res = PredictResponse(ticker="JNJ", predicted_return=0.015, predicted_price_usd=160.5)
    assert isinstance(res.predicted_return, float)
    assert res.ticker == "JNJ"