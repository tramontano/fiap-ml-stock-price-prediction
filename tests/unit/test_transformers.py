import pandas as pd
import pytest

from src.ml.transformers import (
    DailyReturnTransformer,
    EMATransformer,
    FeatureSelector,
    RSITransformer,
)


@pytest.fixture
def sample_data():
    """Cria um DataFrame de exemplo com preços crescentes."""
    return pd.DataFrame(
        {
            "Close": [100, 105, 110, 115, 120, 125, 130, 135, 140, 145],
            "Date": pd.date_range(start="2023-01-01", periods=10),
        }
    )


def test_daily_return_transformer(sample_data):
    transformer = DailyReturnTransformer(column="Close")
    transformed = transformer.transform(sample_data)

    assert "Return_Close" in transformed.columns
    # O primeiro valor deve ser 0 ou bfilled (não NaN)
    assert not transformed["Return_Close"].isna().any()
    # 105 / 100 - 1 = 0.05
    assert transformed["Return_Close"].iloc[1] == pytest.approx(0.05)


def test_ema_transformer(sample_data):
    windows = [2, 5]
    transformer = EMATransformer(windows=windows, column="Close")
    transformed = transformer.transform(sample_data)

    for w in windows:
        col = f"Dist_EMA_{w}"
        assert col in transformed.columns
        assert not transformed[col].isna().any()


def test_rsi_transformer(sample_data):
    transformer = RSITransformer(window=5, column="Close")
    transformed = transformer.transform(sample_data)

    assert "RSI_5" in transformed.columns
    # RSI deve estar entre 0 e 100
    assert transformed["RSI_5"].min() >= 0
    assert transformed["RSI_5"].max() <= 100
    assert not transformed["RSI_5"].isna().any()


def test_feature_selector(sample_data):
    sample_data["Other"] = 1
    features = ["Close"]
    selector = FeatureSelector(features=features)
    transformed = selector.transform(sample_data)

    assert list(transformed.columns) == features
    assert "Other" not in transformed.columns


def test_feature_selector_missing_col(sample_data, capsys):
    selector = FeatureSelector(features=["NonExistent"])
    selector.transform(sample_data)
    captured = capsys.readouterr()
    assert "Aviso: Algumas colunas não foram encontradas" in captured.out
