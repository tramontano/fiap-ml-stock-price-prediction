import os

from sklearn.pipeline import Pipeline

from src.infrastructure.storage_client import StorageClient  # pyrefly: ignore [missing-import]
from src.core.config import settings  # pyrefly: ignore [missing-import]
from src.core.logging import setup_logging  # pyrefly: ignore [missing-import]
from src.ml.transformers import (  # pyrefly: ignore [missing-import]
    DailyReturnTransformer,
    EMATransformer,
    FeatureSelector,
    RSITransformer,
)

logger = setup_logging()


def run_data_processing(ticker: str = "JNJ", parquet_name: str = "data.parquet"):
    storage = StorageClient()

    # ==========================================
    # 1. CAMADA BRONZE -> CAMADA SILVER (Limpeza)
    # ==========================================
    logger.info(f"Carregando dados brutos da camada Bronze ({ticker})...")
    df_bronze = storage.load_parquet(bucket="bronze", file_path=parquet_name)

    logger.info("Limpando dados para a camada Silver...")
    # Removemos linhas vazias e ordenamos pela data (crucial para séries temporais)
    # Nota: O yfinance pode retornar colunas como 'Close' ou 'Close_XYZ' dependendo da versão/ticker.
    # Procuramos a coluna que contém 'Close' e 'Date'
    close_col = [c for c in df_bronze.columns if "Close" in c][0]
    date_col = [c for c in df_bronze.columns if "Date" in c][0]
    df_silver = (
        df_bronze.dropna(subset=[close_col, date_col]).sort_values(date_col).copy()
    )

    # Salva na camada Silver
    storage.save_parquet(df_silver, bucket="silver", file_path=parquet_name)
    logger.info("Dados limpos salvos na camada Silver!")

    # ==========================================
    # 2. CAMADA SILVER -> CAMADA GOLD (Features)
    # ==========================================
    logger.info("Gerando Features para a camada Gold...")

    target_features = [
        "Date",  # Mantemos a data por agora para podermos indexar mais tarde
        "Return_Close",
        "RSI_15",
        "Dist_EMA_5",
        "Dist_EMA_10",
        "Dist_EMA_15",
    ]

    # Identifica a coluna de fechamento real para os transformadores
    actual_close_col = [c for c in df_silver.columns if "Close" in c][0]

    # Pipeline de Features (SEM O SCALER!)
    feature_pipeline = Pipeline(
        [
            ("daily_return", DailyReturnTransformer(column=actual_close_col)),
            ("rsi", RSITransformer(window=15, column=actual_close_col)),
            (
                "ema_distances",
                EMATransformer(windows=[5, 10, 15], column=actual_close_col),
            ),
            ("selector", FeatureSelector(features=target_features)),
        ]
    )

    df_gold = feature_pipeline.fit_transform(df_silver)

    # Salva na camada Gold
    storage.save_parquet(df_gold, bucket="gold", file_path=parquet_name)
    logger.info("Features finais salvas na camada Gold com sucesso!")
    return df_silver, df_gold


if __name__ == "__main__":
    TARGET_TICKER = "JNJ"
    run_data_processing(TARGET_TICKER, "JNJ/19850102_20251230.parquet")
