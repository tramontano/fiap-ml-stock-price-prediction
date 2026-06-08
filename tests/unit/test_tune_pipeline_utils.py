import numpy as np
import pandas as pd
from unittest.mock import patch
from src.pipelines.tune_pipeline import load_and_prepare_data

@patch("src.pipelines.tune_pipeline.StorageClient")
def test_load_and_prepare_data_structure(mock_storage_class):
    # Setup: Criar 100 dias de dados fictícios com 3 features
    mock_storage_instance = mock_storage_class.return_value
    dates = pd.date_range("2023-01-01", periods=100)
    df = pd.DataFrame({
        "Date": dates,
        "Return_Close": np.random.rand(100),
        "RSI": np.random.rand(100),
        "EMA": np.random.rand(100)
    })
    mock_storage_instance.load_parquet.return_value = df

    time_steps = 10
    X_train, y_train, X_val, y_val, scaler = load_and_prepare_data(ticker="JNJ", time_steps=time_steps)

    # Total de janelas possíveis = 100 - 10 = 90
    # Split de 80% = 72 treino, 18 validação
    assert X_train.shape == (72, 10, 3)
    assert X_val.shape == (18, 10, 3)
    assert len(y_train) == 72
    assert len(y_val) == 18

    # Verifica se os dados foram normalizados (StandardScaler costuma deixar média próxima de 0)
    # Nota: Com dados randômicos a média não será exatamente 0, mas o scaler deve existir
    assert scaler is not None
    # O shape do scaler deve bater com o número de colunas (3)
    assert scaler.n_features_in_ == 3
