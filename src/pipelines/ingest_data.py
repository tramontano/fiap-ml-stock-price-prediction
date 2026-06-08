import os
from typing import Union

import yfinance as yf
from pandas import DataFrame

from src.infrastructure.storage_client import StorageClient


def run_ingestion(ticker: str, start_date: str, end_date: str):
    """
    Extrai dados financeiros de uma ação e guarda na camada Bronze do Data Lake.
    """
    print(f"Iniciando a extração de dados para {ticker} ({start_date} a {end_date})...")

    # 1. Extração
    data: Union[DataFrame, None] = yf.download(
        ticker, start=start_date, end=end_date, progress=False
    )

    if data is None or data.empty:
        raise ValueError(f"Não foram encontrados dados para o ticker {ticker}.")

    # 2. Formatação Base
    # O yfinance coloca a Data no index, precisamos dela como uma coluna normal
    data.reset_index(inplace=True)

    # Achata as colunas caso o yfinance retorne um MultiIndex (comum nas novas versões)
    data.columns = [
        "_".join(col).strip() if isinstance(col, tuple) else col for col in data.columns
    ]
    # Remove underscores soltos caso seja apenas um ticker
    data.columns = [
        col.replace("_", "") if col.endswith("_") else col for col in data.columns
    ]

    print(f"Foram extraídas {len(data)} linhas. A preparar para guardar...")

    # 3. Guardar no Armazenamento (Camada Bronze)
    storage = StorageClient()
    file_path = f"{ticker}/raw_data.parquet"

    storage.save_parquet(df=data, bucket="bronze", file_path=file_path)
    print("Ingestão concluída com sucesso")


if __name__ == "__main__":
    # Podemos receber o Ticker e as Datas via variáveis de ambiente (útil para o Airflow depois)
    TARGET_TICKER = os.getenv("TARGET_TICKER", "JNJ")
    START_DATE = os.getenv("START_DATE", "1985-01-01")
    END_DATE = os.getenv("END_DATE", "2025-12-31")

    run_ingestion(TARGET_TICKER, START_DATE, END_DATE)
