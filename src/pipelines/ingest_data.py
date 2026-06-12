import os
from typing import Union

import pandas as pd
import yfinance as yf
from pandas import DataFrame

from src.infrastructure.storage_client import StorageClient  # pyrefly: ignore [missing-import]
from src.core.logging import setup_logging  # pyrefly: ignore [missing-import]
from src.core.config import settings  # pyrefly: ignore [missing-import]

logger = setup_logging()


def run_ingestion(
    ticker: Union[str, None] = None,
    start_date: Union[str, None] = None,
    end_date: Union[str, None] = None,
):
    """
    Extrai dados financeiros de uma ação e guarda na camada Bronze do Data Lake.
    """
    logger.info(f"Iniciando a extração de dados para {ticker}...")

    # 1. Extração
    data: Union[DataFrame, None] = yf.download(
        ticker, start=start_date, end=end_date, group_by="ticker", progress=False
    )
    if data is None or data.empty:
        logger.error(f"Não foram encontrados dados para o ticker {ticker}.")
        raise ValueError(f"Não foram encontrados dados para o ticker {ticker}.")

    # 2. Formatação Base
    # Extract first and last closing dates
    first_date = data.index[0].strftime("%Y%m%d")
    last_date = data.index[-1].strftime("%Y%m%d")
    parquet_name = f"{ticker}/{first_date}_{last_date}.parquet"
    # Achata as colunas caso o yfinance retorne um MultiIndex
    data = data[ticker]
    data.reset_index(inplace=True)
    # O yfinance coloca a Data no index, precisamos dela como uma coluna normal
    data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None)

    logger.info(f"Foram extraídas {len(data)} linhas. Preparando upload...")

    storage = StorageClient()

    # 3. Guardar no Armazenamento (Camada Bronze)
    if storage.file_exists(bucket="bronze", file_path=parquet_name):
        logger.info(f"Arquivo existente, pulando upload: {parquet_name}")
    else:
        storage.save_parquet(data, bucket="bronze", file_path=parquet_name)

    logger.info("Ingestão concluída com sucesso")

    return data, parquet_name


if __name__ == "__main__":
    # Podemos receber o Ticker e as Datas via variáveis de ambiente (útil para o Airflow depois)
    TARGET_TICKER = "JNJ"
    START_DATE = "1985-01-01"
    END_DATE = "2025-12-31"

    run_ingestion(TARGET_TICKER, START_DATE, END_DATE)
