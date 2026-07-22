from src.infrastructure.registry import RegistryClient
from src.infrastructure.storage_client import StorageClient
from src.core.logging import setup_logging
from src.core.config import settings

logger = setup_logging()

def sync_model():
    """
    Sincroniza o modelo para o S3.
    """
    storage = StorageClient()
    client = RegistryClient()
    run_id = client.get_champion_run_id()
    logger.info(f"Run ID: {run_id}")
    if run_id is None:
        logger.error("Não foi possível encontrar o modelo campeão.")
        return False
    if storage.file_exists("models", f"{run_id}/feature_pipeline.pkl") and \
        storage.file_exists("models", f"{run_id}/lstm_model.keras"):
        logger.info("Modelo já existe no S3.")
        return True
    try:
        logger.info("Iniciando sincronização do modelo...")
        client.sync_stage_to_s3("champion")
        logger.info("Modelo sincronizado com sucesso!")
        return True
    except Exception as e:
        logger.error(f"Erro ao sincronizar o modelo: {str(e)}")
        return False

if __name__ == "__main__":
    sync_model()
