import os

import mlflow
import pytest

from src.core.config import settings


def test_mlflow_env_variables_load():
    """
    Valida se as variáveis obrigatórias são carregadas corretamente para o ambiente do processo.
    """
    # Valida presença das chaves críticas
    assert settings.MLFLOW_TRACKING_URI is not None, "MLFLOW_TRACKING_URI ausente"
    assert settings.MLFLOW_TRACKING_USERNAME is not None, (
        "MLFLOW_TRACKING_USERNAME ausente"
    )
    assert settings.MLFLOW_TRACKING_PASSWORD is not None, (
        "MLFLOW_TRACKING_PASSWORD ausente"
    )
    assert "dagshub.com" in settings.MLFLOW_TRACKING_URI, (
        "A URI deve apontar para o DagsHub"
    )


@pytest.mark.integration
def test_mlflow_connection_success():
    """
    Valida a conectividade real. Tenta autenticar no DagsHub e realizar
    uma operação de leitura (search_experiments).
    """

    # Configura o client
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    os.environ["MLFLOW_TRACKING_USERNAME"] = settings.MLFLOW_TRACKING_USERNAME
    os.environ["MLFLOW_TRACKING_PASSWORD"] = settings.MLFLOW_TRACKING_PASSWORD

    try:
        # O método search_experiments exige autenticação válida.
        # Se as credenciais estiverem erradas, o MLflow lançará uma exceção de permissão.
        mlflow.search_runs()
        print("\n[OK] Conexão com MLflow/DagsHub estabelecida com sucesso!")
    except Exception as e:
        pytest.fail(f"Falha na conexão com o MLflow: {e}")
