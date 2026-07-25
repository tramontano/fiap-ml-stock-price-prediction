from datetime import datetime, timedelta

from airflow.sdk import Param, dag, get_current_context, task


@dag(
    schedule="@daily",
    params={
        "ticker": Param("JNJ", type="string"),
        "start_date": Param("1985-01-01", type="string"),
        "end_date": Param(
            (datetime.now() - timedelta(1)).strftime("%Y-%m-%d"), type="string"
        ),
        "train_parameters": Param({}, type="object"),
        "hyperparametrization": Param(True, type="boolean"),
    },
)
def training_pipeline(ds: str = None):

    @task
    def extract_data():
        """Bronze: Extrai dados financeiros do Yahoo Finance e guarda no s3."""
        from src.pipelines.ingest_data import run_ingestion

        ctx = get_current_context()["params"]

        ticker = ctx["ticker"]
        start_date = ctx["start_date"]
        end_date = ctx["end_date"]

        print(
            f"Iniciando Ingestão: ticker={ticker}, start={start_date}, end={end_date}"
        )
        data, parquet_name = run_ingestion(ticker, start_date, end_date)

        return {"parquet_name": parquet_name, "rows": len(data), "ticker": ticker}

    @task
    def transform_data(bronze_data):
        """Silver -> Gold: Limpeza dos dados brutos e Feature Engineering."""
        from src.pipelines.process_data import run_data_processing

        ticker = bronze_data["ticker"]
        parquet_name = bronze_data["parquet_name"]

        print(f"Iniciando Processamento: ticker={ticker}, parquet={parquet_name}")
        df_silver, df_gold = run_data_processing(ticker, parquet_name)

        return {
            "parquet_name": parquet_name,
            "ticker": ticker,
            "silver_rows": len(df_silver),
            "gold_rows": len(df_gold),
        }

    @task
    def load_data(gold_data):
        """Carrega dados da camada GOLD e aplica o StandardScaler."""
        from src.pipelines.tune_pipeline import load_and_prepare_data

        parquet = gold_data["parquet_name"]

        X_train, y_train, X_val, y_val, fitted_pipeline = load_and_prepare_data(
            parquet_name=parquet
        )
        return X_train, y_train, X_val, y_val, fitted_pipeline

    @task
    def get_parameters():
        """Coleta e preparação de parametros"""
        from src.infrastructure.registry import RegistryClient

        context = get_current_context()
        param = context["params"]["train_parameters"]
        if param == {}:
            client = RegistryClient()
            run_id = client.get_champion_run_id()
            champ_param = client.get_run(run_id).data.to_dictionary()["params"]
            print("Usando parâmetros do modelo Champion")
            param = {
                "units": champ_param.get("units", 128),
                "dropout_rate": champ_param.get("dropout_rate", 0.22418282771976486),
                "learning_rate": champ_param.get("learning_rate", 0.00014377259),
                "batch_size": champ_param.get("batch_size", 64),
                "activation": champ_param.get("activation", "relu"),
                "epochs": champ_param.get("epochs", 75),
            }
        else:
            print("Usando parâmetros fornecidos")
            param = {
                "units": param.get("units", 128),
                "dropout_rate": param.get("dropout_rate", 0.22418282771976486),
                "learning_rate": param.get("learning_rate", 0.00014377259),
                "batch_size": param.get("batch_size", 64),
                "activation": param.get("activation", "relu"),
                "epochs": param.get("epochs", 75),
            }
        return param

    @task(multiple_outputs=True)
    def optimize_param(data_tuple):
        """Função de estudo e otimização de hiperparametros"""
        import optuna

        from src.core.config import settings
        from src.infrastructure.registry import RegistryClient
        from src.pipelines.tune_pipeline import objective

        X_train, y_train, X_val, y_val, fitted_pipeline = data_tuple
        client = RegistryClient()
        # Iniciamos uma "run" pai no MLflow para agrupar todas as tentativas do Optuna
        run = client.create_run(run_name=datetime.now().strftime("%Y%m%d_%H%M%S"))
        run_id = run.info.run_id
        # Criando o estudo do Optuna
        study = optuna.create_study(
            direction="minimize",
            study_name="lstm_tuning",
            storage=settings.OPTUNA_STORAGE_URI,
            load_if_exists=True,
        )

        # Executa N tentativas (trials)
        n_trials = settings.OPTUNA_STUDY_TRIALS
        print(
            f"Iniciando o Optuna ({n_trials} tentativas). Pode demorar alguns minutos..."
        )
        study.optimize(
            lambda trial: objective(
                trial, X_train, y_train, X_val, y_val, fitted_pipeline
            ),
            n_trials=n_trials,
            n_jobs=-1,
        )

        print("\nOtimização concluída!")
        print(f"Melhores hiperparâmetros encontrados: {study.best_params}")
        print(f"Menor RMSE atingido: {study.best_value}")

        # Regista os melhores parâmetros na run pai
        client.log_params({"best_" + k: v for k, v in study.best_params.items()})
        client.log_metric("best_rmse", study.best_value)
        client.set_terminated(run_id, "FINISHED")
        return run_id, study.best_params

    @task
    def get_final_parameters(optimized_params=None, base_params=None):
        """
        Retorna os parâmetros finais baseado na decisão de otimização.
        Se use_optimized=True, usa optimized_params. Caso contrário, usa base_params.
        """
        context = get_current_context()
        use_optimized = context["params"]["hyperparametrization"]
        if use_optimized and optimized_params:
            return optimized_params
        else:
            return base_params

    @task
    def train_new_model(param):
        from src.infrastructure.registry import RegistryClient
        from src.pipelines.tune_pipeline import train

        context = get_current_context()
        parquet = context["params"]["parquet_name"]
        train(param, parquet)
        client = RegistryClient()
        run_id = client.tag_challenger()
        return run_id

    @task
    def promote_challenger(run_id):
        from src.infrastructure.registry import RegistryClient

        client = RegistryClient()
        run_id = client.promote_to_champion(run_id)
        client.sync_stage_to_s3("champion")
        return run_id

    # Definindo as dependencias e ordem do pipeline para o AirFlow:
    bronze_data = extract_data()
    gold_data = transform_data(bronze_data)
    data_tuple = load_data(gold_data)
    base_params = get_parameters()
    opt_params = optimize_param(data_tuple)
    params = get_final_parameters(opt_params, base_params)
    challenger_run = train_new_model(params)
    promote_challenger(challenger_run)


training_pipeline()
if __name__ == "__main__":
    dag.test()
