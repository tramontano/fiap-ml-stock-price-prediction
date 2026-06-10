import os

import dagshub
import mlflow
import numpy as np
import optuna
from dotenv import load_dotenv
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
)
from tensorflow.keras.callbacks import EarlyStopping

# Importações da nossa Arquitetura
from src.infrastructure.storage_client import StorageClient
from src.ml.features import create_sequences
from src.ml.model import build_lstm_model

# Carrega as variáveis de ambiente (Credenciais do DagsHub e MinIO)
load_dotenv(".env/mlflow.env")

# Inicializando dagshub
dagshub.init(
    repo_owner="tramontano", repo_name="fiap-ml-stock-price-prediction", mlflow=True
)

# Configuração do MLflow ligada ao DagsHub
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
if MLFLOW_TRACKING_URI:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    # Autenticação via variáveis de ambiente
    os.environ["MLFLOW_TRACKING_USERNAME"] = os.getenv("MLFLOW_TRACKING_USERNAME", "")
    os.environ["MLFLOW_TRACKING_PASSWORD"] = os.getenv("MLFLOW_TRACKING_PASSWORD", "")


def load_and_prepare_data(
    ticker: str = "JNJ", time_steps: int = 20, parquet_name: str = "data.parquet"
):
    """Carrega dados da camada GOLD e aplica o StandardScaler."""
    print("Carregando dados da camada Gold...")
    storage = StorageClient()
    df_gold = storage.load_parquet(bucket="gold", file_path=parquet_name)

    # Indexamos a data e isolamos as features num array NumPy
    df_gold.set_index("Date", inplace=True)
    features_array = df_gold.values

    # Criamos as janelas temporais PRIMEIRO
    print("Criando as janelas temporais (Sliding Windows)...")
    X, y = create_sequences(features_array, time_steps=time_steps)

    # Dividimos em Treino (80%) e Validação (20%) ANTES do Scaler
    split = int(len(X) * 0.8)
    X_train_raw, y_train, X_val_raw, y_val = X[:split], y[:split], X[split:], y[split:]

    # AGORA SIM, o Scaler entra em ação apenas com dados de Treino (evitando Data Leakage)
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()

    # Achata o 3D para 2D, escala, e volta para 3D (truque de NumPy para LSTMs)
    X_train = scaler.fit_transform(
        X_train_raw.reshape(-1, X_train_raw.shape[-1])
    ).reshape(X_train_raw.shape)
    X_val = scaler.transform(X_val_raw.reshape(-1, X_val_raw.shape[-1])).reshape(
        X_val_raw.shape
    )

    return X_train, y_train, X_val, y_val, scaler


def objective(trial, X_train, y_train, X_val, y_val):
    """Função objetivo do Optuna: treina um modelo e devolve o erro a minimizar."""

    # 1. O Optuna sugere hiperparâmetros dinamicamente
    param = {
        "units": trial.suggest_categorical("units", [32, 64, 128]),
        "dropout_rate": trial.suggest_float("dropout_rate", 0.1, 0.4),
        "learning_rate": trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True),
        "batch_size": trial.suggest_categorical("batch_size", [16, 32, 64]),
        # Para acelerar testes, usamos poucas epochs, mas em produção seriam 50-100
        # "epochs": 20
        "epochs": 100,
    }
    # Inicia o tracking no MLflow para esta tentativa (run)
    with mlflow.start_run(nested=True):
        # Regista os parâmetros escolhidos
        mlflow.log_params(param)

        # Constrói o modelo com os parâmetros sugeridos
        model = build_lstm_model(
            input_shape=(X_train.shape[1], X_train.shape[2]),
            units=param["units"],
            dropout_rate=param["dropout_rate"],
            learning_rate=param["learning_rate"],
        )

        # EarlyStopping: para o treino mais cedo se o modelo deixar de aprender
        early_stop = EarlyStopping(
            monitor="val_loss", patience=3, restore_best_weights=True
        )

        # Treina o modelo
        model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=param["epochs"],
            batch_size=param["batch_size"],
            callbacks=[early_stop],
            verbose=0,  # Mantemos silencioso para não poluir o terminal
        )

        # Avaliação final
        y_pred = model.predict(X_val)

        # Calcula as métricas exigidas pelo Tech Challenge
        metricas = {
            "rmse": np.sqrt(mean_squared_error(y_val, y_pred)),
            "mae": mean_absolute_error(y_val, y_pred),
            "mape": mean_absolute_percentage_error(y_val, y_pred),
        }

        # Regista as métricas no MLflow
        mlflow.log_metrics(metricas)

        # Monkey Patch: Injeta a versão no Keras para o MLflow não dar erro
        import tensorflow as tf
        import tensorflow.keras as keras

        if not hasattr(keras, "__version__"):
            keras.__version__ = tf.__version__
        # Guardar o modelo no MLflow se for o melhor até agora
        mlflow.keras.log_model(model, "lstm_model")
        mlflow.sklearn.log_model(fitted_pipeline, "feature_pipeline")

    return metricas["rmse"]  # O Optuna vai tentar MINIMIZAR este valor


if __name__ == "__main__":
    print("Iniciando o pipeline de Tuning...")

    # 1. Preparação dos dados
    X_train, y_train, X_val, y_val, fitted_pipeline = load_and_prepare_data(
        ticker="JNJ", time_steps=20, parquet_name="JNJ/19850102_20251230.parquet"
    )

    # 2. Configura a experiência principal no MLflow
    mlflow.set_experiment("stock-price-lstm")

    # Iniciamos uma "run" pai no MLflow para agrupar todas as tentativas do Optuna
    with mlflow.start_run(run_name="Optuna_Optimization"):
        # 3. Cria o estudo do Optuna
        study = optuna.create_study(direction="minimize", study_name="lstm_tuning")

        # Executa N tentativas (trials)
        print("Iniciando o Optuna (10 tentativas). Pode demorar alguns minutos...")
        study.optimize(
            lambda trial: objective(trial, X_train, y_train, X_val, y_val), n_trials=5
        )

        print("\nOtimização concluída!")
        print(f"Melhores hiperparâmetros encontrados: {study.best_params}")
        print(f"Menor RMSE atingido: {study.best_value}")

        # Regista os melhores parâmetros na run pai
        mlflow.log_params({"best_" + k: v for k, v in study.best_params.items()})
        mlflow.log_metric("best_rmse", study.best_value)
