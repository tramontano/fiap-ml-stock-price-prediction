"""src.infrastructure.registry
================================

Cliente CRUD para o registry de experimentos de Machine Learning,
combinando o MLflow hospedado no DagsHub (tracking de runs/métricas/tags)
com um bucket S3/MinIO (cache de artefatos para serving).

Visão geral das decisões de design
-----------------------------------
1. Estratégia de tags:
   Em vez de usar duas tags booleanas separadas ("Champion"/"Challenger"
   como chaves), este módulo usa uma única chave de tag (`STAGE_TAG_KEY`)
   cujo valor é "Champion" ou "Challenger". Isso garante, por construção,
   que um run nunca tenha os dois estágios simultaneamente, e simplifica
   buscas (`tags.stage = 'Champion'`). As tags são aplicadas a nível de
   *run* do MLflow (não ao Model Registry formal do MLflow), pois os
   requisitos do projeto referenciam diretamente run_id.

2. Política de limpeza (housekeeping):
   A conta DagsHub usada neste projeto tem um limite de ~100 experimentos.
   Por isso, toda vez que `tag_challenger()` é executado (diretamente ou
   via `promote_to_champion()`), todos os runs do experimento que não
   sejam o Champion nem o novo Challenger são removidos do MLflow
   (`delete_run`). Ou seja: apenas Champion e Challenger sobrevivem no
   registry ao final de cada ciclo de tagging/promoção. Os demais runs de
   um ciclo de tuning (ex.: trials do Optuna) são descartados após a
   seleção. Isso é intencional e foi pedido explicitamente, mas vale
   destacar: o histórico de runs antigos não fica preservado no DagsHub
   além de Champion/Challenger.

3. Estrutura de pastas no bucket S3 "models":

       models/
         runs/{run_id}/model.keras    -> binário do modelo LSTM (Keras/TF)
         runs/{run_id}/scaler.pkl     -> scaler/transformer ajustado (joblib)
         pointers/champion.json       -> {"run_id": "..."}
         pointers/challenger.json     -> {"run_id": "..."}

   O artefato fica versionado pelo próprio run_id (`runs/{run_id}/...`) e
   o estágio é apenas um ponteiro pequeno (`pointers/{stage}.json`) que
   aponta para um run_id. Vantagens:
     - Promover Challenger -> Champion não exige reenviar o binário do
       modelo: o artefato já está em `runs/{run_id}/` desde que o
       Challenger foi sincronizado; a promoção só precisa atualizar o
       ponteiro `pointers/champion.json`.
     - `load_model()` (usado em serving) sempre lê de um caminho
       previsível, sem depender de uma chamada ao MLflow em tempo de
       inferência.

Exemplo de uso
--------------
    from src.infrastructure.registry import RegistryClient

    ml_client = RegistryClient()

    # Após uma rodada de tuning (Optuna), promover o melhor run a Challenger:
    challenger_id = ml_client.tag_challenger()
    ml_client.sync_stage_to_s3("challenger")

    # Validado o Challenger, promovê-lo a Champion:
    ml_client.promote_to_champion()
    ml_client.sync_stage_to_s3("champion")

    # Em serving (API de inferência):
    model, scaler, run_id = ml_client.load_model()
"""

from __future__ import annotations

import json
import os
import pickle
import tempfile
from pathlib import Path
from typing import Any

import joblib
import mlflow
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from mlflow.tracking.fluent import log_metrics, log_params, set_experiment, start_run

from src.core.config import settings
from src.core.logging import setup_logging
from src.infrastructure.storage_client import StorageClient

logger = setup_logging()


# -----------------------------------------------------------------------
# Contrato esperado de StorageClient (ver src.infrastructure.storage_client).
# Todas as chamadas a StorageClient ficam isoladas nos métodos privados
# _store_local_file, _fetch_to_local_file, _store_bytes, _fetch_bytes e
# _keys_exist (seção "Ponte com o S3/MinIO" da classe abaixo). Caso a
# assinatura real de StorageClient seja diferente da assumida aqui, basta
# ajustar esses cinco métodos:
#
#   upload(bucket: str, key: str, local_path: str) -> None
#   download(bucket: str, key: str, local_path: str) -> None
#   upload_bytes(bucket: str, key: str, data: bytes) -> None
#   download_bytes(bucket: str, key: str) -> bytes
#   list_objects(bucket: str, prefix: str) -> list[str]
# -----------------------------------------------------------------------


class RegistryClient(MlflowClient):
    """Cliente CRUD para o registry de experimentos (DagsHub + MLflow + S3).

    Encapsula toda a lógica de:
      - inicialização da conexão DagsHub/MLflow;
      - tagging e promoção de runs entre os estágios Challenger e Champion,
        com suporte a rollback manual;
      - limpeza de runs antigos para respeitar o limite de experimentos
        da conta DagsHub;
      - sincronização de artefatos (modelo + scaler) entre o MLflow e um
        bucket S3/MinIO usado como cache de baixa latência para serving;
      - carregamento do modelo/scaler em memória para a API de inferência.

    Attributes:
        client (mlflow.tracking.MlflowClient): Cliente MLflow conectado ao
            servidor de tracking hospedado no DagsHub.
        storage (StorageClient): Cliente de acesso ao S3/MinIO.
        experiment_name (str): Nome do experimento MLflow em uso.
        experiment_id (str): ID do experimento MLflow em uso.

    Example:
        >>> ml_client = RegistryClient()
        >>> model, scaler, run_id = ml_client.load_model()
    """

    # Tag aplicada a nível de run no MLflow para indicar o estágio do modelo.
    STAGE_TAG_KEY: str = "stage"
    CHAMPION_TAG: str = "Champion"
    CHALLENGER_TAG: str = "Challenger"
    DEFAULT_METRIC_KEY: str = "rmse"

    # Bucket e convenção de chaves no S3/MinIO.
    MODELS_BUCKET: str = "models"
    RUNS_PREFIX: str = "runs"
    POINTERS_PREFIX: str = "pointers"

    # ATENÇÃO: ajuste estes dois valores para refletir exatamente o
    # artifact_path usado em tune_pipeline.py ao logar o modelo/scaler no
    # MLflow (ex.: mlflow.log_artifact(local_path, artifact_path=...)).
    MODEL_ARTIFACT_PATH: str = "model"
    SCALER_ARTIFACT_PATH: str = "scaler"

    # ATENÇÃO: assume um modelo Keras/TensorFlow (model.save /
    # tf.keras.models.load_model). Se o projeto usar outro framework
    # (ex.: PyTorch), ajuste apenas _serialize_model e _deserialize_model.
    MODEL_FILENAME: str = "lstm_model.keras"
    SCALER_FILENAME: str = "feature_pipeline.pkl"

    def __init__(self) -> None:
        """Inicializa o RegistryClient.

        Configura a autenticação com o DagsHub, conecta o MlflowClient ao
        servidor de tracking remoto, instancia o StorageClient (S3/MinIO)
        e resolve (ou cria) o experimento de MLflow definido em
        `settings.MLFLOW_EXPERIMENT_NAME`.

        Raises:
            ValueError: Se `settings.DAGSHUB_APP_TOKEN` não estiver configurado.
            MlflowException: Se não for possível conectar ou criar o
                experimento no servidor de tracking.
        """
        super().__init__()

        os.environ["MLFLOW_TRACKING_URI"] = settings.MLFLOW_TRACKING_URI
        os.environ["MLFLOW_TRACKING_USERNAME"] = settings.MLFLOW_TRACKING_USERNAME
        os.environ["MLFLOW_TRACKING_PASSWORD"] = settings.DAGSHUB_APP_TOKEN
        # os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
        self.log_params = log_params
        self.log_metrics = log_metrics
        self.set_experiment = set_experiment
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        self.start_run = start_run
        self.client = mlflow.tracking.MlflowClient()
        self.storage = StorageClient()
        self.experiment_name: str = settings.MLFLOW_EXPERIMENT_NAME
        self.experiment_id: str = self._resolve_experiment_id()
        logger.debug(
            "RegistryClient pronto (experiment_id=%s, experiment_name=%s).",
            self.experiment_id,
            self.experiment_name,
        )

    def _resolve_experiment_id(self) -> str:
        """Obtém o ID do experimento de MLflow, criando-o se necessário.

        Returns:
            str: ID do experimento correspondente a `self.experiment_name`.
        """
        experiment = self.client.get_experiment_by_name(self.experiment_name)
        if experiment is not None:
            logger.debug(
                "Experimento '%s' já existe (id=%s).",
                self.experiment_name,
                experiment.experiment_id,
            )
            return experiment.experiment_id

        experiment_id = self.client.create_experiment(self.experiment_name)
        logger.info(
            "Experimento '%s' criado (id=%s).", self.experiment_name, experiment_id
        )
        return experiment_id

    # ------------------------------------------------------------------
    # Tagging e promoção (Create/Update + Delete de housekeeping)
    # ------------------------------------------------------------------

    def tag_challenger(
        self, run_id: str | None = None, metric_key: str | None = None
    ) -> str | None:
        """Marca um run como Challenger no registry, com rollback opcional.

        Sem `run_id`: busca, entre todos os runs do experimento (exceto o
        run atual de Champion), aquele com o menor valor de `metric_key`
        e o marca como Challenger.

        Com `run_id`: realiza um rollback manual, marcando diretamente o
        run informado como Challenger (ignora a busca por métrica).

        Em ambos os casos, a tag do Challenger anterior é removida (se
        existir e for diferente do novo) e, ao final, todos os runs que
        não sejam o Champion nem o novo Challenger são apagados do
        registry via `_cleanup_other_runs`, respeitando o limite de
        experimentos da conta DagsHub.

        Args:
            run_id (str | None): ID do run a promover manualmente a
                Challenger (rollback). Se None, seleciona automaticamente
                o run com melhor `metric_key`. Default: None.
            metric_key (str | None): Métrica usada para escolher o melhor
                run quando `run_id` não é informado. Default:
                `DEFAULT_METRIC_KEY` ("rmse").

        Returns:
            str | None: O run_id marcado como Challenger, ou None se
                nenhum run candidato for encontrado (apenas no modo
                automático).

        Raises:
            ValueError: Se o run resolvido for o mesmo run_id do Champion
                atual.
        """
        metric_key = metric_key or self.DEFAULT_METRIC_KEY
        champion_id = self.get_champion_run_id()
        old_challenger_id = self.get_challenger_run_id()

        if run_id is not None:
            new_challenger_id = run_id
            logger.info("Rollback manual de Challenger solicitado para run %s.", run_id)
        else:
            new_challenger_id = self._select_best_run(
                exclude_run_id=champion_id, metric_key=metric_key
            )
            if new_challenger_id is None:
                logger.error(
                    "Nenhum run candidato a Challenger encontrado (métrica='%s').",
                    metric_key,
                )
                return None

        if new_challenger_id == champion_id:
            logger.error(
                "Run %s é o Champion atual; não pode também ser Challenger.",
                new_challenger_id,
            )
            raise ValueError(f"Run {new_challenger_id} já é o Champion atual.")

        if old_challenger_id and old_challenger_id != new_challenger_id:
            self._remove_tag_if_present(old_challenger_id, self.STAGE_TAG_KEY)
            logger.info("Tag Challenger removida do run %s.", old_challenger_id)

        self.client.set_tag(new_challenger_id, self.STAGE_TAG_KEY, self.CHALLENGER_TAG)
        logger.info("Run %s marcado como Challenger.", new_challenger_id)

        # keep_ids = {rid for rid in (champion_id, new_challenger_id) if rid}
        # self._cleanup_other_runs(keep_ids)

        return new_challenger_id

    def promote_to_champion(self, run_id: str | None = None) -> str:
        """Promove o Challenger atual (ou `run_id` informado) a Champion.

        Sem `run_id`: promove o run atualmente marcado como Challenger.

        Com `run_id`: realiza um rollback manual de Champion, promovendo
        diretamente o run informado (ignora o Challenger atual).

        Remove a tag Champion do run anterior (se houver) e a tag
        Challenger do novo Champion (caso ele a tivesse, já que está
        deixando de ser Challenger). Em seguida, dispara
        `tag_challenger()` para reavaliar quem deve ser o próximo
        Challenger entre os runs remanescentes — o que também aciona a
        limpeza de runs descrita em `tag_challenger`.

        Args:
            run_id (str | None): run_id a promover/rollback diretamente
                para Champion. Se None, usa o Challenger atual.
                Default: None.

        Returns:
            str: run_id promovido a Champion.

        Raises:
            ValueError: Se `run_id` não for informado e não houver
                Challenger marcado no momento da chamada.
        """
        new_champion_id = run_id or self.get_challenger_run_id()
        if new_champion_id is None:
            logger.error("Nenhum Challenger encontrado para promover a Champion.")
            raise ValueError(
                "Não há Challenger marcado; informe run_id explicitamente."
            )

        old_champion_id = self.get_champion_run_id()
        if old_champion_id == new_champion_id:
            logger.info("Run %s já é o Champion atual; nada a fazer.", new_champion_id)
            return new_champion_id

        if old_champion_id:
            self._remove_tag_if_present(old_champion_id, self.STAGE_TAG_KEY)
            logger.info("Tag Champion removida do run %s.", old_champion_id)

        self._remove_tag_if_present(new_champion_id, self.STAGE_TAG_KEY)
        self.client.set_tag(new_champion_id, self.STAGE_TAG_KEY, self.CHAMPION_TAG)
        logger.info("Run %s promovido a Champion.", new_champion_id)

        self.tag_challenger()

        return new_champion_id

    def delete_run(self, run_id: str) -> bool:
        """Remove um run do registry MLflow/DagsHub.

        Args:
            run_id (str): ID do run a ser removido.

        Returns:
            bool: True se removido com sucesso, False caso contrário.
        """
        try:
            self.client.delete_run(run_id)
            logger.info("Run %s removido do registry.", run_id)
            return True
        except MlflowException as e:
            logger.error("Falha ao remover run %s: %s", run_id, e)
            return False

    def _cleanup_other_runs(self, keep_run_ids: set[str]) -> None:
        """Apaga todos os runs do experimento, exceto os informados.

        Usado para manter apenas Champion e Challenger no registry,
        respeitando o limite de experimentos da conta DagsHub. Artefatos
        já espelhados em `runs/{run_id}/` no S3 (caso existam) não são
        afetados por esta limpeza — apenas o registro no MLflow é
        removido.

        Args:
            keep_run_ids (set[str]): Conjunto de run_ids que não devem
                ser removidos.
        """
        runs = self.client.search_runs([self.experiment_id])
        for run in runs:
            if run.info.run_id not in keep_run_ids:
                self.delete_run(run.info.run_id)

    def _select_best_run(
        self, exclude_run_id: str | None, metric_key: str
    ) -> str | None:
        """Retorna o run_id com o menor valor de `metric_key` no experimento.

        Args:
            exclude_run_id (str | None): run_id a excluir da busca
                (tipicamente o Champion atual, para não rebaixá-lo a
                Challenger).
            metric_key (str): Nome da métrica de comparação (menor valor
                é considerado melhor, ex.: "rmse").

        Returns:
            str | None: run_id do melhor candidato, ou None se a lista
                de candidatos estiver vazia.
        """
        runs = self.client.search_runs([self.experiment_id])
        candidates = [
            r
            for r in runs
            if r.info.run_id != exclude_run_id and metric_key in r.data.metrics
        ]
        if not candidates:
            return None
        best = min(candidates, key=lambda r: r.data.metrics[metric_key])
        return best.info.run_id

    def _remove_tag_if_present(self, run_id: str, key: str) -> None:
        """Remove uma tag de um run, ignorando o erro caso ela não exista.

        Args:
            run_id (str): ID do run.
            key (str): Nome da tag a remover.
        """
        try:
            self.client.delete_tag(run_id, key)
        except MlflowException:
            logger.debug("Run %s não possuía a tag '%s' para remover.", run_id, key)

    # ------------------------------------------------------------------
    # Leitura de estágio (Read)
    # ------------------------------------------------------------------

    def get_champion_run_id(self) -> str | None:
        """Retorna o run_id atualmente marcado como Champion.

        Returns:
            str | None: run_id do Champion, ou None se nenhum run
                estiver marcado.
        """
        return self._get_run_id_by_stage(self.CHAMPION_TAG)

    def get_challenger_run_id(self) -> str | None:
        """Retorna o run_id atualmente marcado como Challenger.

        Returns:
            str | None: run_id do Challenger, ou None se nenhum run
                estiver marcado.
        """
        return self._get_run_id_by_stage(self.CHALLENGER_TAG)

    def _get_run_id_by_stage(self, stage_value: str) -> str | None:
        """Busca o run_id cuja tag `STAGE_TAG_KEY` é igual a `stage_value`.

        Args:
            stage_value (str): "Champion" ou "Challenger".

        Returns:
            str | None: run_id correspondente, ou None se não encontrado.
        """
        runs = self.client.search_runs(
            [self.experiment_id],
            filter_string=f"tags.{self.STAGE_TAG_KEY} = '{stage_value}'",
            max_results=1,
        )
        return runs[0].info.run_id if runs else None

    # ------------------------------------------------------------------
    # Ponte com o S3/MinIO (bucket "models"). Todas as chamadas a
    # StorageClient ficam isoladas nestes cinco métodos — ver contrato
    # esperado no topo do módulo.
    # ------------------------------------------------------------------

    def _store_local_file(self, key: str, local_path: Path) -> None:
        """Envia um arquivo local para `MODELS_BUCKET/key`."""
        self.storage.upload(str(local_path), self.MODELS_BUCKET, key)

    def _fetch_to_local_file(self, key: str, local_path: Path) -> None:
        """Baixa `MODELS_BUCKET/key` para um arquivo local."""
        self.storage.download(str(local_path), self.MODELS_BUCKET, key)

    def _store_bytes(self, key: str, data: bytes) -> None:
        """Envia bytes em memória para `MODELS_BUCKET/key`."""
        self.storage.upload_bytes(data, self.MODELS_BUCKET, key)

    def _fetch_bytes(self, key: str) -> bytes:
        """Baixa `MODELS_BUCKET/key` como bytes em memória."""
        return self.storage.download_bytes(self.MODELS_BUCKET, key)

    def _keys_exist(self, prefix: str) -> bool:
        """Indica se já existe ao menos um objeto sob `prefix` no bucket."""
        return bool(self.storage.folder_exists(self.MODELS_BUCKET, prefix))

    # ------------------------------------------------------------------
    # Serialização do modelo (ponto único de ajuste por framework)
    # ------------------------------------------------------------------

    def _serialize_model(self, model: Any, destination: Path) -> None:
        """Serializa o modelo LSTM em disco.

        ATENÇÃO: assume um modelo Keras/TensorFlow (`model.save(path)`).
        Se o projeto usar outro framework, ajuste este método e
        `_deserialize_model`.

        Args:
            model (Any): Instância do modelo treinado.
            destination (Path): Caminho local de destino.
        """
        model.save(str(destination))

    def _deserialize_model(self, source: Path) -> Any:
        """Desserializa o modelo LSTM a partir do disco.

        ATENÇÃO: assume um modelo Keras/TensorFlow
        (`tf.keras.models.load_model`). Se o projeto usar outro
        framework, ajuste este método e `_serialize_model`.

        Args:
            source (Path): Caminho local do arquivo do modelo.

        Returns:
            Any: Modelo desserializado, pronto para inferência.
        """
        import tensorflow as tf  # import local: evita exigir TF em contextos que só fazem tagging

        return tf.keras.models.load_model(str(source))

    # ------------------------------------------------------------------
    # Sincronização MLflow <-> S3 e carregamento para serving
    # ------------------------------------------------------------------

    def store_model_to_s3(self, model: Any, scaler: Any, run_id: str) -> None:
        """Serializa e envia para o S3 um modelo e scaler em memória.

        Os artefatos são gravados em `runs/{run_id}/` no bucket
        `MODELS_BUCKET`, sem alterar nenhum ponteiro de estágio
        (Champion/Challenger). Use `sync_stage_to_s3` para isso.

        Args:
            model (Any): Modelo LSTM treinado, em memória.
            scaler (Any): Scaler/transformer ajustado durante o treino.
            run_id (str): run_id de origem, usado para nomear o prefixo
                no S3.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / self.MODEL_FILENAME
            scaler_path = Path(tmp_dir) / self.SCALER_FILENAME

            self._serialize_model(model, model_path)
            joblib.dump(scaler, scaler_path)

            prefix = f"{self.RUNS_PREFIX}/{run_id}/"
            self._store_local_file(f"{prefix}{self.MODEL_FILENAME}", model_path)
            self._store_local_file(f"{prefix}{self.SCALER_FILENAME}", scaler_path)

        logger.info(
            "Modelo e scaler do run %s enviados para s3://%s/%s.",
            run_id,
            self.MODELS_BUCKET,
            prefix,
        )

    def sync_stage_to_s3(self, stage: str) -> str | None:
        """Sincroniza um estágio (Champion ou Challenger) do MLflow para o S3.

        Resolve o run_id atual do estágio no DagsHub/MLflow, garante que
        os artefatos desse run existam em `runs/{run_id}/` no S3
        (baixando do MLflow apenas se ainda não estiverem lá) e atualiza
        o ponteiro `pointers/{stage}.json`.

        Args:
            stage (str): "champion" ou "challenger" (case-insensitive).

        Returns:
            str | None: run_id sincronizado, ou None se nenhum run
                estiver marcado para o estágio informado.

        Raises:
            ValueError: Se `stage` não for "champion" nem "challenger".
        """
        stage = stage.lower()
        valid_stages = {self.CHAMPION_TAG.lower(), self.CHALLENGER_TAG.lower()}
        if stage not in valid_stages:
            raise ValueError(
                f"Estágio inválido: '{stage}'. Use 'champion' ou 'challenger'."
            )

        run_id = (
            self.get_champion_run_id()
            if stage == self.CHAMPION_TAG.lower()
            else self.get_challenger_run_id()
        )
        if run_id is None:
            logger.error("Nenhum run marcado como %s no MLflow.", stage)
            return None

        prefix = f"{self.RUNS_PREFIX}/{run_id}/"
        if not self._keys_exist(prefix):
            self._download_mlflow_artifacts_to_s3(run_id)
        else:
            logger.debug(
                "Artefatos do run %s já presentes no S3; reaproveitando.", run_id
            )

        self._update_stage_pointer(stage, run_id)
        return run_id

    def _download_mlflow_artifacts_to_s3(self, run_id: str) -> None:
        """Baixa os artefatos de modelo e scaler de um run do MLflow e os envia ao S3.

        Os artefatos são renomeados para `MODEL_FILENAME`/`SCALER_FILENAME`
        ao chegar no S3, independentemente do nome usado dentro do
        artifact store do MLflow — isso mantém `load_model()` simples,
        sempre lendo um caminho previsível.

        Args:
            run_id (str): run_id de origem no DagsHub/MLflow.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_downloaded = mlflow.artifacts.download_artifacts(
                run_id=run_id,
                artifact_path=self.MODEL_ARTIFACT_PATH,
                dst_path=tmp_dir,
            )
            scaler_downloaded = mlflow.artifacts.download_artifacts(
                run_id=run_id,
                artifact_path=self.SCALER_ARTIFACT_PATH,
                dst_path=tmp_dir,
            )
            model_local_path = self._resolve_artifact_file(
                model_downloaded, self.MODEL_FILENAME
            )
            scaler_local_path = self._resolve_artifact_file(
                scaler_downloaded, self.SCALER_FILENAME
            )

            prefix = f"{self.RUNS_PREFIX}/{run_id}/"
            self._store_local_file(f"{prefix}{self.MODEL_FILENAME}", model_local_path)
            self._store_local_file(f"{prefix}{self.SCALER_FILENAME}", scaler_local_path)

        logger.info(
            "Artefatos do run %s baixados do MLflow e enviados ao S3 (%s).",
            run_id,
            prefix,
        )

    def _resolve_artifact_file(self, downloaded_path: str, preferred_name: str) -> Path:
        """Resolve o caminho de um único arquivo a partir do retorno de
        `mlflow.artifacts.download_artifacts`.

        `download_artifacts` retorna um arquivo diretamente apenas quando
        `artifact_path` já inclui o nome do arquivo. Quando `artifact_path`
        aponta para um diretório (caso comum quando o artefato foi logado
        via `mlflow.log_artifact(local_path, artifact_path=<diretorio>)`
        ou via uma API `log_model` específica de framework), o retorno é
        um diretório — este método localiza o arquivo correto dentro dele.

        Args:
            downloaded_path (str): Caminho retornado por
                `download_artifacts`.
            preferred_name (str): Nome de arquivo preferido a procurar
                dentro do diretório, caso `downloaded_path` seja um
                diretório (ex.: `MODEL_FILENAME`).

        Returns:
            Path: Caminho local de um único arquivo.

        Raises:
            FileNotFoundError: Se `downloaded_path` for um diretório vazio.
        """
        path = Path(downloaded_path)
        if path.is_file():
            return path

        candidate = path / preferred_name
        if candidate.is_file():
            return candidate

        files = [f for f in path.iterdir() if f.is_file()]
        if not files:
            raise FileNotFoundError(
                f"Nenhum arquivo encontrado em '{downloaded_path}'."
            )
        if len(files) > 1:
            logger.debug(
                "Múltiplos arquivos em '%s'; usando '%s'. Ajuste MODEL_ARTIFACT_PATH/"
                "SCALER_ARTIFACT_PATH se este não for o arquivo correto.",
                downloaded_path,
                files[0].name,
            )
        return files[0]

    def _update_stage_pointer(self, stage: str, run_id: str) -> None:
        """Atualiza o ponteiro `pointers/{stage}.json` para apontar para `run_id`.

        Args:
            stage (str): "champion" ou "challenger".
            run_id (str): run_id a apontar.
        """
        key = f"{self.POINTERS_PREFIX}/{stage}.json"
        payload = json.dumps({"run_id": run_id}).encode("utf-8")
        self._store_bytes(key, payload)
        logger.info("Ponteiro de estágio '%s' atualizado para run %s.", stage, run_id)

    def _read_stage_pointer(self, stage: str) -> str | None:
        """Lê o run_id atualmente apontado por `pointers/{stage}.json`.

        Args:
            stage (str): "champion" ou "challenger".

        Returns:
            str | None: run_id apontado, ou None se o ponteiro não
                existir ou não puder ser lido.
        """
        key = f"{self.POINTERS_PREFIX}/{stage}.json"
        try:
            data = self._fetch_bytes(key)
            logger.info(f"Ponteiro de estágio '{stage}' lido com sucesso: {data}")
            return json.loads(data)["run_id"]
        except Exception as e:  # noqa: BLE001 - leitura de ponteiro é best-effort
            logger.error(f"Falha ao ler ponteiro de estágio '{stage}': {e}")
            return None

    def load_model(self, stage: str = "champion") -> tuple[Any, Any, str]:
        """Carrega o modelo e o scaler de serving para a memória.

        O estágio carregado depende de `settings.ENVIRONMENT`:
        "production" carrega o Champion; qualquer outro valor (ex.:
        "local") carrega o Challenger. A leitura é feita a partir do
        cache em S3 (não do MLflow diretamente) — rode `sync_stage_to_s3`
        antes de implantar uma nova versão para manter esse cache
        atualizado.

        Returns:
            tuple[Any, Any, str]: (model, scaler, run_id), onde `model`
                é o modelo LSTM pronto para inferência, `scaler` é o
                transformer ajustado no treino, e `run_id` identifica a
                origem para fins de log/métricas na API de inferência.

        Raises:
            RuntimeError: Se não houver ponteiro de estágio publicado no
                S3 (ou seja, `sync_stage_to_s3` nunca foi executado para
                esse estágio).
        """
        run_id = self._read_stage_pointer(stage)
        if run_id is None:
            raise RuntimeError(
                f"Nenhum ponteiro de estágio '{stage}' encontrado em s3://{self.MODELS_BUCKET}."
            )

        prefix = f"{self.RUNS_PREFIX}/{run_id}/"

        model_file_exists = self.storage.file_exists(
            self.MODELS_BUCKET, f"{prefix}{self.MODEL_FILENAME}"
        )
        scaler_file_exists = self.storage.file_exists(
            self.MODELS_BUCKET, f"{prefix}{self.SCALER_FILENAME}"
        )
        # Monkey Patch: Injeta a versão no Keras para o MLflow não dar erro
        import tensorflow as tf
        import tensorflow.keras as keras

        if not hasattr(keras, "__version__"):
            keras.__version__ = tf.__version__  # type: ignore

        local_path = f"{self.MODELS_BUCKET}/{prefix}"
        if not model_file_exists or not scaler_file_exists:
            logger.info(
                f"Arquivos não encontrados em s3://{self.MODELS_BUCKET}/{prefix}."
                " Baixando do MLflow."
            )

            if not os.path.exists(local_path):
                os.makedirs(local_path, exist_ok=True)

                scaler = mlflow.sklearn.load_model(f"runs:/{run_id}/feature_pipeline")
                model = mlflow.keras.load_model(f"runs:/{run_id}/lstm_model")

                model.save(f"{local_path}/{self.MODEL_FILENAME}")  # type: ignore
                pickle.dump(scaler, open(f"{local_path}/{self.SCALER_FILENAME}", "wb"))

            # Upload para o S3 (Fonte da verdade para a API)
            self.storage.upload(
                self.MODELS_BUCKET,
                self.MODELS_BUCKET,
                f"{prefix}{self.MODEL_FILENAME}",
            )
            self.storage.upload(
                self.MODELS_BUCKET,
                self.MODELS_BUCKET,
                f"{prefix}{self.SCALER_FILENAME}",
            )

        if not os.path.isfile(
            f"{local_path}{self.MODEL_FILENAME}"
        ) or not os.path.isfile(f"{local_path}{self.SCALER_FILENAME}"):
            os.makedirs(local_path, exist_ok=True)
            self.storage.download(
                self.MODELS_BUCKET,
                self.MODELS_BUCKET,
                f"{prefix}{self.MODEL_FILENAME}",
            )
            self.storage.download(
                self.MODELS_BUCKET,
                self.MODELS_BUCKET,
                f"{prefix}{self.SCALER_FILENAME}",
            )

        scaler = pickle.load(open(f"{local_path}{self.SCALER_FILENAME}", "rb"))
        model = tf.keras.models.load_model(f"{local_path}{self.MODEL_FILENAME}")

        logger.info(
            "Modelo carregado para serving: estágio=%s, run_id=%s.", stage, run_id
        )
        return model, scaler, run_id

    def get_run_metrics(self, run_id: str) -> dict[str, float] | None:
        """Retorna as métricas de uma run."""
        try:
            run = self.client.get_run(run_id)
            metrics = run.data.to_dictionary()["metrics"]
            if not metrics:
                logger.warning("Métricas da run com ID %s não encontradas.", run_id)
                return None
            return metrics
        except Exception as e:
            logger.error("Erro ao obter métricas da run %s: %s", run_id, e)
            return None

    def get_run_params(self, run_id: str) -> dict[str, float] | None:
        """Retorna os parametros de uma run."""
        try:
            run = self.client.get_run(run_id)
            params = run.data.to_dictionary()["params"]
            if not params:
                logger.warning("Parametros da run com ID %s não encontrados.", run_id)
                return None
            return params
        except Exception as e:
            logger.error("Erro ao obter parametros da run %s: %s", run_id, e)
            return None

    def get_model_creation_date(self, run_id: str) -> str | None:
        """Retorna a data de criação do modelo."""
        try:
            run = self.client.get_run(run_id)
            tags = run.data.to_dictionary()["tags"]["mlflow.log-model.history"]
            if not tags:
                logger.warning("Métricas da run com ID %s não encontradas.", run_id)
                return None
            return json.loads(tags)[0]["utc_time_created"]
        except Exception as e:
            logger.error("Erro ao obter métricas da run %s: %s", run_id, e)
            return None


# Teste rápido via linha de comando (Smoke-test)
if __name__ == "__main__":
    client = RegistryClient()
    challenger_id = client.get_challenger_run_id()
    print(f"Challenger ID: {challenger_id}")
    champion_id = client.get_champion_run_id()
    print(f"Champion ID: {champion_id}")
    #    # client.tag_challenger() #1 Tag um modelo para challenger
    #    # client.promote_to_champion() #2 Promove o challenger para champion
    #    # client.sync_stage_to_s3("Champion") #3 Sincroniza o champion para o S3
    model, scaler, run_id = client.load_model()  # Carrega o modelo champion
    print(f"Modelo carregado: {model}")
    print(f"Scaler carregado: {scaler}")
    print(f"Run ID: {run_id}")
