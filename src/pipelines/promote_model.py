import os
import pickle
import sys
from typing import Optional

import dagshub
import tensorflow as tf
from mlflow.tracking import MlflowClient

from src.core.config import settings
from src.core.logging import setup_logging
from src.infrastructure.storage_client import (
    StorageClient,
)

logger = setup_logging()


def from_mlflow_to_s3(
    model: Optional[tf.keras.Model] = None,
    scaler: Optional[pickle.Pickler] = None,
    run_id: Optional[str] = None,
):
    """
    Baixa o artefato da run promovida no MLflow, faz o upload para o S3
    e valida fisicamente a existência do arquivo no bucket.
    """
    storage = StorageClient()
    bucket = "models"
    model_name = "lstm_model.keras"
    scaler_name = "feature_pipeline.pkl"
    local_path = "models/" + settings.ENVIRONMENT

    try:
        from src.ml.inference import load_artifacts

        # 1. Download do DagsHub/MLflow para a memória
        model, scaler, run_id = load_artifacts(run_id)

        # 2. Salvar na pasta models/<environment>
        os.makedirs(local_path, exist_ok=True)
        model.save(f"{local_path}/{model_name}")  # type: ignore
        pickle.dump(scaler, open(f"{local_path}/{scaler_name}", "wb"))

        # 3. Upload para o S3 (Fonte da verdade para a API)
        storage.upload(local_path, bucket, model_name)
        storage.upload(local_path, bucket, scaler_name)

        # Limpeza do arquivo temporário local
        if os.path.exists(local_path):
            os.remove(f"{local_path}/{model_name}")
            os.remove(f"{local_path}/{scaler_name}")
            os.removedirs(local_path)

    except Exception as e:
        logger.error(f"Falha inesperada durante a sincronização do artefato: {e}")
        raise


def promote_model():
    dagshub.init(
        repo_owner="tramontano",
        repo_name="fiap-ml-stock-price-prediction",
        mlflow=True,
    )
    # Instanciando variaveis para MLFlow
    MLFLOW_S3_ENDPOINT_URL = settings.S3_ENDPOINT_URL  # noqa: F841
    MLFLOW_S3_IGNORE_TLS = True  # noqa: F841
    AWS_ACCESS_KEY_ID = settings.MINIO_ROOT_USER  # noqa: F841
    AWS_SECRET_ACCESS_KEY = settings.MINIO_ROOT_PASSWORD  # noqa: F841
    client = MlflowClient(settings.MLFLOW_TRACKING_URI)
    experiment_name = "stock-price-lstm"

    # 1. Obter o experimento
    experiment = client.get_experiment_by_name(experiment_name)
    if not experiment:
        logger.info(f"Erro: Experimento '{experiment_name}' não encontrado.")
        sys.exit(1)

    # 2. Buscar todas as runs finalizadas com a métrica RMSE
    logger.info("Buscando runs no MLflow...")
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id], filter_string="metrics.rmse > 0"
    )

    if not runs:
        logger.info("Nenhuma run com métrica 'rmse' encontrada.")
        sys.exit(0)

    # Ordenar localmente por RMSE ascendente para garantir compatibilidade
    runs = sorted(runs, key=lambda r: r.data.metrics.get("rmse", float("inf")))
    best_run = runs[0]
    best_run_id = best_run.info.run_id
    best_rmse = best_run.data.metrics.get("rmse")

    logger.info(
        f"Melhor Run encontrada nos experimentos: ID={best_run_id} com RMSE={best_rmse:.5f}"
    )

    # 3. Identificar o Champion atual via tag 'stage' de run
    champion_run = None
    for run in runs:
        if run.data.tags.get("stage") == "Production":
            champion_run = run
            break

    if not champion_run:
        # Não há champion atual, o melhor se torna Champion imediatamente
        logger.info("Nenhum modelo marcado como Champion (Production) encontrado.")
        logger.info(
            f"Promovendo Run {best_run_id} diretamente para Champion (Production) via tag..."
        )

        # Marcar via tag do MLflow (amplamente suportado pelo DagsHub)
        client.set_tag(best_run_id, "stage", "Production")
        logger.info(f"Sucesso: Run {best_run_id} promovida a Champion (Production).")

    champion_run_id = champion_run.info.run_id
    champion_rmse = champion_run.data.metrics.get("rmse", float("inf"))
    logger.info(f"Champion Atual: Run={champion_run_id}, RMSE={champion_rmse:.5f}")

    # Se o melhor run já for o Champion atual
    if best_run_id == champion_run_id:
        logger.info(
            f"O Champion atual (Run {champion_run_id}) já é a melhor opção baseada em RMSE."
        )

    # Comparar RMSE (Menor é melhor)
    if best_rmse < champion_rmse:
        logger.info(
            f"O Challenger (RMSE={best_rmse:.5f}) é melhor que o Champion (RMSE={champion_rmse:.5f})!"
        )
        logger.info(f"Promovendo Run {best_run_id} para Champion (Production)...")

        # Remove a tag de Production do antigo champion
        client.set_tag(champion_run_id, "stage", "Archived")
        # Promove o novo para Production
        client.set_tag(best_run_id, "stage", "Production")

        # Compilando e subindo modelo para o Data Lake
        from_mlflow_to_s3(best_run_id)

        logger.info(f"Sucesso: Run {best_run_id} promovida para Champion (Production).")
    else:
        logger.info(
            f"O Challenger (RMSE={best_rmse:.5f}) NÃO superou o Champion (RMSE={champion_rmse:.5f})."
        )
        # Marca como Staging (Challenger)
        client.set_tag(best_run_id, "stage", "Staging")
        logger.info(
            f"Mantendo o atual Champion em produção e marcando a Run {best_run_id} como Staging (Challenger)."
        )
    return best_run_id


if __name__ == "__main__":
    run_id = None
    if not run_id:
        run_id = promote_model()
    from_mlflow_to_s3(run_id=run_id)
