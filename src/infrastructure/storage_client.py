import os
from io import BytesIO

import boto3
import pandas as pd
from botocore.exceptions import ClientError


class StorageClient:
    """
    Cliente que abstrai as operações de leitura e escrita no Data Lake (MinIO/AWS S3).
    """

    def __init__(self):
        # Em produção (AWS), podemos deixar estes valores vazios e o boto3 usa as roles do IAM
        self.endpoint_url = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        self.access_key = os.getenv("MINIO_ROOT_USER", "admin")
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", "admin123")

        # Inicializa o cliente S3
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="us-east-1",  # Padrão
        )

    def save_parquet(self, df: pd.DataFrame, bucket: str, file_path: str) -> None:
        """Salva um DataFrame num bucket em formato Parquet."""
        try:
            # Escreve o parquet na memória em vez de criar um ficheiro no disco local
            parquet_buffer = BytesIO()
            df.to_parquet(parquet_buffer, index=False)

            self.s3_client.put_object(
                Bucket=bucket, Key=file_path, Body=parquet_buffer.getvalue()
            )
            print(f"Ficheiro guardado com sucesso: s3://{bucket}/{file_path}")
        except Exception as e:
            print(f"Erro ao guardar ficheiro no S3: {e}")
            raise e

    def load_parquet(self, bucket: str, file_path: str) -> pd.DataFrame:
        """Carrega um ficheiro Parquet do Data Lake para um DataFrame."""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=file_path)
            parquet_content = response["Body"].read()
            return pd.read_parquet(BytesIO(parquet_content))
        except Exception as e:
            print(f"Erro ao ler ficheiro do S3: {e}")
            raise e

    def file_exists(self, bucket: str, file_path: str) -> bool:
        """Verifica se um ficheiro já existe no bucket do Data Lake."""
        try:
            self.s3_client.head_object(Bucket=bucket, Key=file_path)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            # Qualquer outro erro (403 permissões, rede, etc.)
            raise e
