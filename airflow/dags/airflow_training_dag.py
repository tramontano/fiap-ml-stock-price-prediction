from airflow.sdk import Param, dag, get_current_context, task
from src.core.logging import setup_logging

logger = setup_logging()


@dag(
    params={
        "parquet_name": Param("JNJ/19850102_20251230.parquet", type="string"),
        "parameters": Param(
            {
                "units": 128,
                "dropout_rate": 0.22418282771976486,
                "learning_rate": 0.00014377259,
                "batch_size": 64,
                "activation": "relu",
                "epochs": 75,
            },
            type="object",
        ),
    }
)
def training_pipeline(ds: str = None):

    @task
    def load_dataset():
        """Carrega dados da camada GOLD e aplica o StandardScaler."""
        from src.pipelines.tune_pipeline import load_and_prepare_data

        context = get_current_context()
        parquet = context["params"]["parquet_name"]
        X_train, y_train, X_val, y_val, fitted_pipeline = load_and_prepare_data(
            parquet_name=parquet
        )
        return X_train, y_train, X_val, y_val, fitted_pipeline

    @task
    def get_parameters():
        """Coleta e preparação de parametros"""
        from src.infrastructure.registry import RegistryClient

        context = get_current_context()
        param = context["params"]["parameters"]
        if param == {}:
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
        return param

    @task
    def optimize_param():
        """Função de estudo e otimização de hiperparametros"""
        return 1

    @task
    def training_model_a():
        return 1

    @task
    def training_mode_b():
        return 2

    @task
    def training_model_c():
        return 3

    @task.branch
    def choose_best_model(accuracies):
        if max(accuracies) > 2:
            return accurate()
        return inaccurate()

    @task
    def accurate():
        return print("accurate")

    @task
    def inaccurate():
        return print("inaccurate")

    accuracies = [training_model_a(), training_mode_b(), training_model_c()]
    choose_best_model(accuracies)


if __name__ == "__main__":
    dag.test(run_conf={"my_int_param": 42})
training_pipeline()
