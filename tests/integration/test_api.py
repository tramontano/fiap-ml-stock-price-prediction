import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.config import settings


@pytest.fixture
def mock_artifacts():
    """Mocka a transferência do S3 e carregamento do modelo no arranque (lifespan)."""
    with patch("src.api.main._download_and_load_artifacts") as mock:
        # Retorna a tupla (model, pipeline, run_id)
        mock.return_value = (MagicMock(), MagicMock(), "test-run-123")
        yield mock


@pytest.fixture
def mock_predict():
    """Mocka a função de inferência que roda o LSTM."""
    with patch("src.api.routes.predict") as mock:
        mock.return_value = {
            "return_pred": [0.015],
            "return_std_dev": [0.002],
            "confidence_score": [95.5],
            "price_pred": [155.50],
            "dates": [datetime.date(2026, 6, 14)],
            "model_id": "test-run-123",
        }
        yield mock


@pytest.fixture
def client(mock_artifacts):
    """
    Cliente de teste do FastAPI.
    O uso do bloco 'with' força a execução do `lifespan` (boot/shutdown).
    """
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    """Garante que a rota de verificação de saúde da infraestrutura responde 200 OK."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_predict_success(client, mock_predict):
    """Garante que a rota de inferência retorna as chaves corretas e HTTP 200."""
    payload = {"ticker": "JNJ"}
    response = client.post(f"{settings.API_V1_STR}/predict", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "JNJ"
    assert data["predicted_price_usd"] == 155.50
    assert data["confidence_score"] == 95.5
    assert data["prediction_model"] == "test-run-123"
    assert "prediction_date_iso" in data


def test_predict_missing_payload(client):
    """Garante que o Pydantic Schema bloqueia chamadas sem Ticker (HTTP 422)."""
    payload = {}  # Payload vazio
    response = client.post(f"{settings.API_V1_STR}/predict", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_predict_missing_artifacts(client):
    """
    Garante que a API retorna HTTP 503 (Serviço Indisponível) se o modelo
    ou scaler não foram carregados com sucesso no boot (evita erros silenciosos 500).
    """
    # Forçar a remoção dos artefatos da memória (simulando falha de S3)
    app.state.model = None
    app.state.pipeline = None

    payload = {"ticker": "JNJ"}
    response = client.post(f"{settings.API_V1_STR}/predict", json=payload)

    assert response.status_code == 503
    assert "não estão disponíveis" in response.json()["detail"]
