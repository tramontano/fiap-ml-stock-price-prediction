import tomllib
from pathlib import Path
from typing import Literal, Optional, Union

from pydantic_settings import BaseSettings, SettingsConfigDict

# Lê a versão do pyproject.toml globalmente para evitar que variáveis temporárias (como arquivos abertos) sejam capturadas pela classe Settings
_pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
with _pyproject_path.open("rb") as _f:
    _pyproject_data = tomllib.load(_f)


class Settings(BaseSettings):
    # ==========================================
    # Configurações Globais da Aplicação
    # ==========================================
    PROJECT_NAME: str = _pyproject_data["project"]["name"]
    PROJECT_VERSION: str = _pyproject_data["project"]["version"]
    PROJECT_DESCRIPTION: str = _pyproject_data["project"]["description"]
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000"]

    # ==========================================
    # Storage (S3 / MinIO Local)
    # ==========================================
    AWS_REGION: str = "us-east-1"

    # Se estiver preenchido, o boto3/s3fs aponta para cá (MinIO).
    # Se for None, aponta automaticamente para a AWS.
    S3_ENDPOINT_URL: Optional[str] = None
    MLFLOW_S3_ENDPOINT_URL: Optional[str] = S3_ENDPOINT_URL
    # MinIO (Simulador de S3 da AWS)
    MINIO_ROOT_USER: Optional[str] = None
    MINIO_ROOT_PASSWORD: Optional[str] = None

    # ==========================================
    # Model Registry & Tracking (DagsHub / MLflow / OPTUNA)
    # ==========================================
    MLFLOW_TRACKING_URI: Union[str, None] = None
    MLFLOW_TRACKING_USERNAME: Optional[str] = None
    MLFLOW_TRACKING_PASSWORD: Optional[str] = None
    MLFLOW_EXPERIMENT_NAME: Optional[str] = None
    MLFLOW_EXPERIMENT_ID: Optional[str] = None
    DAGSHUB_REPO_NAME: Optional[str] = None
    DAGSHUB_APP_TOKEN: Optional[str] = None
    OPTUNA_STORAGE_URI: Optional[str] = None
    MODEL_STAGE: Literal["champion", "challenger"] = "champion"

    # ==========================================
    # Autenticação de Rotas API
    # ==========================================
    API_USERNAME: str = None
    API_PASSWORD: str = None

    # Configuração do Pydantic para ler do arquivo .env quando rodar localmente
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignora variáveis no .env que não estejam mapeadas aqui
    )


# Instanciamos a classe uma única vez.
# Isso funciona como um Singleton para toda a aplicação.
settings = Settings()
