"""
Loads a trained LSTM + fitted scaler from MLflow and runs predictions
on new Gold-layer data fetched from Data Lake.
"""

import mlflow

from src.infrastructure.storage_client import StorageClient
from src.ml.features import create_sequences
from src.pipelines.ingest_data import run_ingestion
from src.pipelines.process_data import run_data_processing


# Artifact loader
def load_artifacts(run_id: str) -> tuple:
    """
    Fetches the Keras model and the sklearn scaler logged during a specific
    MLflow run.

    Args:
        run_id: MLflow run ID of the Optuna child run that produced the
                best model (copy from the MLflow UI or `study.best_trial`).

    Returns:
        (model, scaler) — ready to use, no fitting needed.
    """
    # Monkey Patch: Injeta a versão no Keras para o MLflow não dar erro
    import tensorflow as tf
    import tensorflow.keras as keras

    if not hasattr(keras, "__version__"):
        keras.__version__ = tf.__version__

    model_uri = f"runs:/{run_id}/lstm_model"
    scaler_uri = f"runs:/{run_id}/feature_pipeline"

    model = mlflow.keras.load_model(model_uri)
    scaler = mlflow.sklearn.load_model(scaler_uri)

    return model, scaler


# Core inference function
def predict(
    ticker: str,
    run_id: str,
    time_steps: int = 20,
    model=None,
    scaler=None,
) -> dict:
    """
    End-to-end inference: Gold data → scaled sequences → predictions.

    Args:
        ticker:     Ticker symbol, e.g. "JNJ". Must match the Gold parquet path.
        run_id:     MLflow run ID used to load model + scaler when not supplied
                    directly (see `model` / `scaler` args below).
        time_steps: Must equal the value used during training (default 30).
        model:      Optional — pass a pre-loaded Keras model to skip MLflow I/O.
        scaler:     Optional — pass the pre-loaded StandardScaler directly.
                    Useful inside FastAPI to load once at startup and reuse.

    Returns:
        dict with keys:
            - return_pred: np.ndarray of raw Return_Close predictions (model output)
            - price_pred:  np.ndarray of Close price predictions (postprocessed)
            - dates:       DatetimeIndex aligned to each prediction

    Raises:
        ValueError: if the Gold parquet has fewer rows than `time_steps`.
    """
    # Loads raw data from last 30d to Bronze bucket
    _, parquet_name = run_ingestion(ticker)
    # Processes Bronze layer into Silver and Gold after clean & feature engineering
    df_silver, df_gold = run_data_processing(ticker, parquet_name)

    # 1. Load artifacts from MLflow only if not injected
    if model is None or scaler is None:
        model, scaler = load_artifacts(run_id)

    storage = StorageClient()

    # 2. Gold layer — engineered features only (no Close column after FeatureSelector)
    #    Columns: [Return_Close, RSI_15, Dist_EMA_5, Dist_EMA_10, Dist_EMA_15]
    df_gold.set_index("Date", inplace=True)
    features_array = df_gold.values  # shape: (n_rows, 5)

    if len(features_array) < time_steps:
        raise ValueError(
            f"Not enough rows ({len(features_array)}) for time_steps={time_steps}."
        )

    # 3. Silver layer — needed ONLY for Close price to postprocess return → price.
    #    Gold dropped Close via FeatureSelector; Silver still has it.
    close_col = [c for c in df_silver.columns if "Close" in c][0]
    date_col = [c for c in df_silver.columns if "Date" in c][0]
    df_silver = df_silver.set_index(date_col)[close_col]

    # Align Silver Close to Gold dates — guards against any row-count mismatch.
    # close_alignedclose_aligned = df_silver.reindex(df_gold.index)

    # 4. Build sequences from RAW Gold data — mirrors training order exactly.
    #    y_raw = Return_Close (column 0), never scaled during training.
    X_raw, _ = create_sequences(features_array, time_steps=time_steps)
    # X_raw shape: (n_samples, time_steps, 5)

    # 5. Scale X only — same transform applied during training.
    X = scaler.transform(X_raw.reshape(-1, X_raw.shape[-1])).reshape(X_raw.shape)

    # 6. Predict — output is Return_Close scalar, NOT a price.
    y_pred_return = model.predict(X).flatten()  # shape: (n_samples,)

    # 7. Postprocess: Return_Close → Close price.
    #    Prediction k predicts Return_Close at Gold row (k + time_steps).
    #    The anchor Close is the LAST day of that window → Gold row (k + time_steps - 1).
    #    Close_{t} = Close_{t-1} * (1 + Return_Close_pred)
    pred_dates = df_gold.index[time_steps : time_steps + len(y_pred_return)]
    anchor_dates = df_gold.index[time_steps - 1 : time_steps - 1 + len(y_pred_return)]

    # Use the actual Close price from Silver layer as the anchor
    anchor_close = df_silver.loc[anchor_dates].values
    y_pred_price = anchor_close * (1 + y_pred_return)

    return {
        "return_pred": y_pred_return,  # raw model output (Return_Close)
        "price_pred": y_pred_price,  # postprocessed Close price
        "dates": pred_dates,  # DatetimeIndex aligned to each prediction
    }


# Quick CLI smoke-test
if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv(".env/mlflow.env")
    # dagshub.init(
    #    repo_owner="tramontano",
    #    repo_name="fiap-ml-stock-price-prediction",
    #    mlflow=True,
    # )
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
    os.environ["MLFLOW_TRACKING_USERNAME"] = os.getenv("MLFLOW_TRACKING_USERNAME", "")
    os.environ["MLFLOW_TRACKING_PASSWORD"] = os.getenv("MLFLOW_TRACKING_PASSWORD", "")
    os.environ["BEST_RUN_ID"] = os.getenv("BEST_RUN_ID", "")

    RUN_ID = os.environ["BEST_RUN_ID"]

    result = predict(ticker="JNJ", run_id=RUN_ID, time_steps=20)
    print(f"Predictions shape  : {result['price_pred'].shape}")
    print(f"Last 5 prices (pred): {result['price_pred'][-5:]}")
    print(f"Last 5 returns(pred): {result['return_pred'][-5:]}")
