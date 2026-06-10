import numpy as np
from sklearn.pipeline import Pipeline

from src.ml.transformers import (
    DailyReturnTransformer,
    EMATransformer,
    FeatureSelector,
    RSITransformer,
)


def build_feature_pipeline() -> Pipeline:
    """
    Constrói e devolve o pipeline completo de Feature Engineering.
    A ordem de execução é sequencial e crucial!
    """

    # Definimos quais são as features FINAIS que queremos que o LSTM veja
    target_features = [
        "Return_Close",
        "RSI_15",
        "Dist_EMA_20",
        "Dist_EMA_100",
        "Dist_EMA_150",
    ]

    features = Pipeline(
        steps=[
            # 1. Calcula o retorno diário
            ("daily_return", DailyReturnTransformer(column="Close")),
            # 2. Calcula o RSI
            ("rsi", RSITransformer(window=15, column="Close")),
            # 3. Calcula as distâncias para as EMAs
            ("ema_distances", EMATransformer(windows=[5, 10, 15], column="Close")),
            # 4. Remove o 'Close', 'Open', 'High', etc., deixando apenas as features estacionárias
            ("selector", FeatureSelector(features=target_features)),
            # 5. Coloca todas as features na mesma escala (Média 0, Desvio Padrão 1)
            # O LSTM precisa disto para não dar mais peso ao RSI (escala 0-100) do que aos retornos
            # (escala -0.1 a 0.1)
            # ("scaler", StandardScaler()),
        ]
    )

    return features


def create_sequences(data: np.ndarray, time_steps: int = 20) -> tuple:
    """
    Transforma um array 2D de features num formato 3D supervisionado para o LSTM.
    Retorna X (features) e y (alvo a prever).
    """
    X, y = [], []
    for i in range(len(data) - time_steps):
        X.append(data[i : (i + time_steps)])
        # Assume que o alvo (Retorno) está na coluna 0.
        # No nosso pipeline, 'Return_Close' é de fato a primeira feature.
        y.append(data[i + time_steps, 0])

    return np.array(X), np.array(y)
