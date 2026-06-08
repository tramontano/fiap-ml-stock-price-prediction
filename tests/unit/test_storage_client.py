from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.infrastructure.storage_client import StorageClient


@pytest.fixture
def mock_s3():
    with patch("boto3.client") as mock_client:
        yield mock_client


def test_save_parquet(mock_s3):
    # Setup
    client_instance = mock_s3.return_value
    storage = StorageClient()
    df = pd.DataFrame({"a": [1, 2]})

    # Execute
    storage.save_parquet(df, "bucket", "path.parquet")

    # Assert
    client_instance.put_object.assert_called_once()
    args, kwargs = client_instance.put_object.call_args
    assert kwargs["Bucket"] == "bucket"
    assert kwargs["Key"] == "path.parquet"
    assert isinstance(kwargs["Body"], bytes)


def test_load_parquet(mock_s3):
    # Setup
    client_instance = mock_s3.return_value
    df_original = pd.DataFrame({"a": [1, 2]})
    buffer = BytesIO()
    df_original.to_parquet(buffer, index=False)
    client_instance.get_object.return_value = {
        "Body": MagicMock(read=lambda: buffer.getvalue())
    }

    storage = StorageClient()
    df_loaded = storage.load_parquet("bucket", "path.parquet")

    pd.testing.assert_frame_equal(df_original, df_loaded)
