import os
import pickle
from datetime import datetime

import dagshub
import mlflow
import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from tensorflow.keras.callbacks import EarlyStopping  # type: ignore

from src.core.config import settings
from src.core.logging import setup_logging
from src.infrastructure.registry import RegistryClient

# Importações da nossa Arquitetura
from src.infrastructure.storage_client import StorageClient
from src.ml.features import create_sequences
from src.ml.model import build_lstm_model

logger = setup_logging()


# Inicializando dagshub
if settings.MLFLOW_TRACKING_URI:
    MLFLOW_S3_IGNORE_TLS = True
    MLFLOW_S3_ENDPOINT_URL = settings.S3_ENDPOINT_URL
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    # Autenticação via variáveis de ambiente
    dagshub.init(
        repo_owner="tramontano",
        repo_name="fiap-ml-stock-price-prediction",
        mlflow=True,
    )

    mlflow.autolog()


def load_and_prepare_data(time_steps: int = 20, parquet_name: str = "data.parquet"):
    """Carrega dados da camada GOLD e aplica o StandardScaler."""
    logger.info("Carregando dados da camada Gold...")
    storage = StorageClient()
    df_gold = storage.load_parquet(bucket="gold", file_path=parquet_name)

    # Indexamos a data e isolamos as features num array NumPy
    df_gold.set_index("Date", inplace=True)
    features_array = df_gold.values

    # Criamos as janelas temporais PRIMEIRO
    logger.info("Criando as janelas temporais (Sliding Windows)...")
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
        "activation": trial.suggest_categorical(
            "activation", ["tanh", "relu", "leaky_relu", "elu"]
        ),
        # Para acelerar testes, usamos poucas epochs, mas em produção seriam 50-100
        # "epochs": 20
        "epochs": 75,
    }
    # Inicia o tracking no MLflow para esta tentativa (run)
    with mlflow.start_run(nested=True) as child_run:
        run_id = child_run.info.run_id
        # Regista os parâmetros escolhidos
        mlflow.log_params(param)

        # Constrói o modelo com os parâmetros sugeridos
        model = build_lstm_model(
            input_shape=(X_train.shape[1], X_train.shape[2]),
            units=param["units"],
            dropout_rate=param["dropout_rate"],
            learning_rate=param["learning_rate"],
            activation=param["activation"],
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
            verbose=0
            if settings.ENVIRONMENT == "production"
            else 1,  # Mantemos silencioso para não poluir o terminal
            use_multiprocessing=True,
        )

        # Avaliação final
        y_pred = model.predict(X_val)

        # Calcula as métricas exigidas pelo Tech Challenge
        metricas = {
            "rmse": np.sqrt(mean_squared_error(y_val, y_pred)),
            "mae": mean_absolute_error(y_val, y_pred),
            "mape": mean_absolute_percentage_error(y_val, y_pred),
            "r2": r2_score(y_val, y_pred),
        }

        # Regista as métricas no MLflow
        mlflow.log_metrics(metricas)

        # Monkey Patch: Injeta a versão no Keras para o MLflow não dar erro
        import tensorflow as tf
        import tensorflow.keras as keras  # type: ignore

        if not hasattr(keras, "__version__"):
            keras.__version__ = tf.__version__  # type: ignore
        # Guardar o modelo no MLflow se for o melhor até agora
        mlflow.keras.log_model(model, "lstm_model")
        mlflow.sklearn.log_model(fitted_pipeline, "feature_pipeline")
        # MLFlow não está salvando o modelo localmente, então vamos salvar manualmente
        local_path = f"models/runs/{run_id}"
        os.makedirs(local_path, exist_ok=True)
        model.save(f"{local_path}/lstm_model.keras")
        pickle.dump(fitted_pipeline, open(f"{local_path}/feature_pipeline.pkl", "wb"))
        try:
            storage = StorageClient()
            storage.upload(f"{local_path}", "models", f"{run_id}/lstm_model.keras")
            storage.upload(f"{local_path}", "models", f"{run_id}/feature_pipeline.pkl")
        except Exception as e:
            logger.warning(f"Falha ao subir modelo para o S3: {e}")

    return metricas["rmse"]  # O Optuna vai tentar MINIMIZAR este valor


def train(param: dict = None, parquet_name: str = None):
    logger.info("Iniciando o pipeline de Tuning...")
    if param is None:
        client = RegistryClient()
        run_id = client.get_champion_run_id()
        param = client.get_run(run_id).data.to_dictionary()["params"]
        logger.info("Usando parâmetros do modelo Champion")
        param = {
            "units": param.get("units", 128),
            "dropout_rate": param.get("dropout_rate", 0.22418282771976486),
            "learning_rate": param.get("learning_rate", 0.00014377259),
            "batch_size": param.get("batch_size", 64),
            "activation": param.get("activation", "relu"),
            "epochs": param.get("epochs", 75),
        }
    else:
        logger.info("Usando parâmetros fornecidos")
        param = {
            "units": param.get("units", 128),
            "dropout_rate": param.get("dropout_rate", 0.22418282771976486),
            "learning_rate": param.get("learning_rate", 0.00014377259),
            "batch_size": param.get("batch_size", 64),
            "activation": param.get("activation", "relu"),
            "epochs": param.get("epochs", 75),
        }
    # 1. Preparação dos dados
    X_train, y_train, X_val, y_val, fitted_pipeline = load_and_prepare_data(
        time_steps=20, parquet_name="JNJ/19850102_20251230.parquet"
    )

    # 2. Configura o experimento principal no MLflow
    mlflow.set_experiment("stock-price-lstm")
    mlflow.autolog()
    # Iniciamos uma "run" pai no MLflow para agrupar todas as tentativas do Optuna
    with mlflow.start_run(run_name=datetime.now().strftime("%Y%m%d_%H%M%S")) as run_id:
        run_id = run_id.info.run_id
        # Regista os parâmetros escolhidos
        mlflow.log_params(param)

        # Constrói o modelo com os parâmetros sugeridos
        model = build_lstm_model(
            input_shape=(X_train.shape[1], X_train.shape[2]),
            units=param["units"],
            dropout_rate=param["dropout_rate"],
            learning_rate=param["learning_rate"],
            activation=param["activation"],
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
            verbose=0
            if settings.ENVIRONMENT == "production"
            else 1,  # Mantemos silencioso para não poluir o terminal
            use_multiprocessing=True,
        )

        # Avaliação final
        y_pred = model.predict(X_val)

        # Calcula as métricas exigidas pelo Tech Challenge
        metricas = {
            "rmse": np.sqrt(mean_squared_error(y_val, y_pred)),
            "mae": mean_absolute_error(y_val, y_pred),
            "mape": mean_absolute_percentage_error(y_val, y_pred),
            "r2": r2_score(y_val, y_pred),
        }

        # Regista as métricas no MLflow
        mlflow.log_metrics(metricas)

        # Monkey Patch: Injeta a versão no Keras para o MLflow não dar erro
        import tensorflow as tf
        import tensorflow.keras as keras  # type: ignore

        if not hasattr(keras, "__version__"):
            keras.__version__ = tf.__version__  # type: ignore
        # Guardar o modelo no MLflow se for o melhor até agora
        mlflow.keras.log_model(model, "lstm_model")
        mlflow.sklearn.log_model(fitted_pipeline, "feature_pipeline")
        # MLFlow não está salvando o modelo localmente, então vamos salvar manualmente
        local_path = f"models/runs/{run_id}"
        os.makedirs(local_path, exist_ok=True)
        model.save(f"{local_path}/lstm_model.keras")
        pickle.dump(fitted_pipeline, open(f"{local_path}/feature_pipeline.pkl", "wb"))
        try:
            storage = StorageClient()
            storage.upload(f"{local_path}", "models", f"{run_id}/lstm_model.keras")
            storage.upload(f"{local_path}", "models", f"{run_id}/feature_pipeline.pkl")
        except Exception as e:
            logger.warning(f"Falha ao subir modelo para o S3: {e}")


if __name__ == "__main__":
    train(parquet_name="JNJ/19850102_20251230.parquet")
#    logger.info("Iniciando o pipeline de Tuning...")
#
#    # 1. Preparação dos dados
#    X_train, y_train, X_val, y_val, fitted_pipeline = load_and_prepare_data(
#        time_steps=20, parquet_name="JNJ/19850102_20251230.parquet"
#    )
#
#    # 2. Configura a experiência principal no MLflow
#    mlflow.set_experiment("stock-price-lstm")
#    mlflow.autolog()
#    # Iniciamos uma "run" pai no MLflow para agrupar todas as tentativas do Optuna
#    with mlflow.start_run(run_name=datetime.now().strftime("%Y%m%d_%H%M%S")):
#        # 3. Cria o estudo do Optuna
#        study = optuna.create_study(
#            direction="minimize",
#            study_name="lstm_tuning",
#            storage=settings.OPTUNA_STORAGE_URI,
#            load_if_exists=True,
#        )
#
#        # Executa N tentativas (trials)
#        n_trials = 2
#        logger.info(
#            f"Iniciando o Optuna ({n_trials} tentativas). Pode demorar alguns minutos..."
#        )
#        study.optimize(
#            lambda trial: objective(trial, X_train, y_train, X_val, y_val),
#            n_trials=n_trials,
#            n_jobs=-1,
#        )
#
#        logger.info("\nOtimização concluída!")
#        logger.info(f"Melhores hiperparâmetros encontrados: {study.best_params}")
#        logger.info(f"Menor RMSE atingido: {study.best_value}")
#
#        # Regista os melhores parâmetros na run pai
#        mlflow.log_params({"best_" + k: v for k, v in study.best_params.items()})
#        mlflow.log_metric("best_rmse", study.best_value)
#        # Regista os melhores parâmetros na run pai
#        mlflow.log_params({"best_" + k: v for k, v in study.best_params.items()})
#        mlflow.log_metric("best_rmse", study.best_value)
