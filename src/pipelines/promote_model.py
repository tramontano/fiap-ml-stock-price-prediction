"""src.pipelines.promote_model
=============================

Script de automação para comparar e promover o modelo Challenger a Champion
baseado na métrica de desempenho (RMSE), sincronizando os artefatos com o S3.
"""

import sys
from src.infrastructure.registry import RegistryClient
from src.core.logging import setup_logging

logger = setup_logging()

def main():
    logger.info("Iniciando processo de avaliação e promoção de modelos...")
    client = RegistryClient()
    
    try:
        champion_id = client.get_champion_run_id()
        challenger_id = client.get_challenger_run_id()
        
        if not challenger_id:
            logger.warning("Nenhum modelo Challenger encontrado no registro para avaliar.")
            sys.exit(0)
            
        logger.info(f"Modelo Challenger encontrado: {challenger_id}")
        
        # Se não há Champion, promove diretamente
        if not champion_id:
            logger.info("Nenhum Champion atual encontrado. Promovendo Challenger diretamente...")
            client.promote_to_champion(challenger_id)
            client.sync_stage_to_s3("champion")
            client.sync_stage_to_s3("challenger")
            logger.info("Promoção inicial concluída com sucesso!")
            sys.exit(0)
            
        logger.info(f"Modelo Champion atual: {champion_id}")
        
        # Recupera as métricas
        champion_metrics = client.get_run_metrics(champion_id) or {}
        challenger_metrics = client.get_run_metrics(challenger_id) or {}
        
        champion_rmse = champion_metrics.get("rmse", float("inf"))
        challenger_rmse = challenger_metrics.get("rmse", float("inf"))
        
        logger.info(f"Métricas (RMSE) -> Champion: {champion_rmse:.6f} | Challenger: {challenger_rmse:.6f}")
        
        if challenger_rmse < champion_rmse:
            logger.info(f"Challenger ({challenger_rmse:.6f}) é melhor que o Champion ({champion_rmse:.6f}). Promovendo...")
            client.promote_to_champion(challenger_id)
            client.sync_stage_to_s3("champion")
            client.sync_stage_to_s3("challenger")
            logger.info("Modelo Challenger promovido a Champion com sucesso!")
        else:
            logger.info(f"Challenger ({challenger_rmse:.6f}) não superou o Champion ({champion_rmse:.6f}). Nenhuma promoção efetuada.")
            
    except Exception as e:
        logger.error(f"Erro inesperado durante a promoção do modelo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
