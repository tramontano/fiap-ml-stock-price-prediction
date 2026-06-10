import os

import mlflow
import pytest
from dotenv import load_dotenv


def test_mlflow_env_variables_load():
    """
    Valida se o ficheiro .env/mlflow.env existe e se as variáveis obrigatórias
    são carregadas corretamente para o ambiente do processo.
    """
    # Caminho relativo ao root do projeto
    env_path = ".env/mlflow.env"

    # 1. Verifica existência física
    assert os.path.exists(env_path), (
        f"Ficheiro de ambiente não encontrado em: {env_path}"
    )

    # 2. Carrega as variáveis
    load_dotenv(env_path)

    # 3. Valida presença das chaves críticas
    assert os.getenv("MLFLOW_TRACKING_URI") is not None, "MLFLOW_TRACKING_URI ausente"
    assert os.getenv("MLFLOW_TRACKING_USERNAME") is not None, (
        "MLFLOW_TRACKING_USERNAME ausente"
    )
    assert os.getenv("MLFLOW_TRACKING_PASSWORD") is not None, (
        "MLFLOW_TRACKING_PASSWORD ausente"
    )
    assert "dagshub.com" in os.getenv("MLFLOW_TRACKING_URI"), (
        "A URI deve apontar para o DagsHub"
    )


@pytest.mark.integration
def test_mlflow_connection_success():
    """
    Valida a conectividade real. Tenta autenticar no DagsHub e realizar
    uma operação de leitura (search_experiments).
    """
    load_dotenv(".env/mlflow.env")

    # Configura o client
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
    os.environ["MLFLOW_TRACKING_USERNAME"] = os.getenv("MLFLOW_TRACKING_USERNAME", "")
    os.environ["MLFLOW_TRACKING_PASSWORD"] = os.getenv("MLFLOW_TRACKING_PASSWORD", "")

    try:
        # O método search_experiments exige autenticação válida.
        # Se as credenciais estiverem erradas, o MLflow lançará uma exceção de permissão.
        mlflow.search_runs()
        print("\n[OK] Conexão com MLflow/DagsHub estabelecida com sucesso!")
    except Exception as e:
        pytest.fail(f"Falha na conexão com o MLflow: {e}")
