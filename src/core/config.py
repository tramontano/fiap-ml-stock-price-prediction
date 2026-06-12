from typing import Optional, Literal, Union
import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==========================================
    # Configurações Globais da Aplicação
    # ==========================================
    # Lê a versão do pyproject.toml — fonte única de verdade
    _pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with _pyproject_path.open("rb") as _f:
        PROJECT_NAME: str = tomllib.load(_f)["project"]["name"]
        PROJECT_VERSION: str = tomllib.load(_f)["project"]["version"]
        PROJECT_DESCRIPTION: str = tomllib.load(_f)["project"]["description"]
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
    # Model Registry & Tracking (DagsHub / MLflow)
    # ==========================================
    MLFLOW_TRACKING_URI: Union[str, None] = None
    MLFLOW_TRACKING_USERNAME: Optional[str] = None
    MLFLOW_TRACKING_PASSWORD: Optional[str] = None

    # Configuração do Pydantic para ler do arquivo .env quando rodar localmente
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignora variáveis no .env que não estejam mapeadas aqui
    )


# Instanciamos a classe uma única vez.
# Isso funciona como um Singleton para toda a aplicação.
settings = Settings()
