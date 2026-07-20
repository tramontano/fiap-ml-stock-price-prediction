import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.pipelines.ingest_data import run_ingestion

@pytest.fixture
def mock_yfinance_data():
    """Simula o retorno de um MultiIndex do yfinance."""
    cols = pd.MultiIndex.from_tuples([("JNJ", "Close"), ("JNJ", "Open")])
    df = pd.DataFrame([[100, 99], [101, 100]], columns=cols)
    df.index = pd.to_datetime(["2023-01-01", "2023-01-02"])
    df.index.name = "Date"
    return df

@patch("src.pipelines.ingest_data.yf.download")
@patch("src.pipelines.ingest_data.StorageClient")
def test_run_ingestion_success(mock_storage_class, mock_yf_download, mock_yfinance_data):
    # Configuração
    mock_storage_instance = mock_storage_class.return_value
    mock_storage_instance.file_exists.return_value = False
    mock_yf_download.return_value = mock_yfinance_data

    # Execução
    run_ingestion("JNJ", "2023-01-01", "2023-01-02")

    # Verificações
    mock_yf_download.assert_called_once()
    mock_storage_instance.save_parquet.assert_called_once()

    # Verifica se as colunas foram "achatadas" corretamente (ex: Close_JNJ ou Close)
    saved_df = mock_storage_instance.save_parquet.call_args[0][0]
    assert "Date" in saved_df.columns
    assert any("Close" in col for col in saved_df.columns)

@patch("src.pipelines.ingest_data.yf.download")
def test_run_ingestion_empty_error(mock_yf_download):
    """Testa o comportamento quando o ticker não existe."""
    mock_yf_download.return_value = pd.DataFrame()

    with pytest.raises(ValueError, match="Não foram encontrados dados"):
        run_ingestion("INVALID_TICKER", "2023-01-01", "2023-01-02")