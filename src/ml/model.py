from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam


def build_lstm_model(
    input_shape: tuple,
    units: int = 64,
    dropout_rate: float = 0.2,
    learning_rate: float = 0.001,
    activation: str = "tanh",
) -> Sequential:
    """
    Constrói e compila dinamicamente a arquitetura do modelo LSTM.

    Args:
        input_shape: Formato da entrada (time_steps, n_features).
        units: Número de neurônios na camada LSTM.
        dropout_rate: Taxa de dropout para evitar overfitting.
        learning_rate: Taxa de aprendizagem do otimizador Adam.
    """
    model = Sequential(
        [
            LSTM(units, activation=activation, input_shape=input_shape),
            Dropout(dropout_rate),
            Dense(1),  # Prevemos o retorno do dia seguinte
        ]
    )

    model.compile(
        optimizer=Adam(learning_rate=learning_rate), loss="mse", metrics=["mae"]
    )
    return model
