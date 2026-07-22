from sklearn.base import BaseEstimator, TransformerMixin


class DailyReturnTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, column="Close"):
        self.column = column

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_transformed = X.copy()
        X_transformed[f"Return_{self.column}"] = X_transformed[self.column].pct_change()
        return X_transformed.bfill()


class EMATransformer(BaseEstimator, TransformerMixin):
    """Adiciona Média Móvel Exponencial (EMA) usando apenas Pandas."""

    def __init__(self, windows=[20, 100, 150], column="Close"):
        self.windows = windows
        self.column = column

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_transformed = X.copy()
        for window in self.windows:
            col_name = f"EMA_{window}_{self.column}"
            # span=window simula o comportamento exato da EMA do mercado financeiro
            # Distância percentual da EMA
            # Dessa forma, o resultado será algo como +0.02 ou -0.015
            # mantendo os dados estacionários e saudáveis para o LSTM
            ema_value = X_transformed[self.column].ewm(span=window, adjust=False).mean()
            X_transformed[f"Dist_EMA_{window}"] = (
                X_transformed[self.column] - ema_value
            ) / ema_value
        return X_transformed


class RSITransformer(BaseEstimator, TransformerMixin):
    """Calcula o Relative Strength Index (RSI) nativamente."""

    def __init__(self, window=15, column="Close"):
        self.window = window
        self.column = column

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_transformed = X.copy()
        # 1. Calcula a diferença de preço dia a dia
        delta = X_transformed[self.column].diff()
        # 2. Separa dias de ganho e dias de perda
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        # 3. Calcula a média móvel exponencial das perdas e ganhos (Wilder's Smoothing)
        avg_gain = gain.ewm(alpha=1 / self.window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / self.window, adjust=False).mean()
        # 4. Calcula o RS e o RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        X_transformed[f"RSI_{self.window}"] = rsi
        X_transformed.bfill(inplace=True)  # Preenche os NaNs iniciais
        return X_transformed


class FeatureSelector(BaseEstimator, TransformerMixin):
    """Filtra apenas as colunas estacionárias finais para alimentar o modelo."""

    def __init__(self, features):
        self.features = features

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        # Retorna apenas as colunas selecionadas, descartando o resto (como o 'Close' bruto)
        # Verifica quais colunas realmente existem para evitar KeyError
        existing_features = [f for f in self.features if f in X.columns]

        if len(existing_features) < len(self.features):
            print(
                f"Aviso: Algumas colunas não foram encontradas: {set(self.features) - set(existing_features)}"
            )

        return X[existing_features].copy()
