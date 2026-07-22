"""
Carrega um modelo LSTM treinado + scaler ajustado a partir do MLflow e executa
previsões em novos dados da camada Gold (Ouro) buscados no Data Lake.
"""

import numpy as np

from src.core.logging import setup_logging
from src.infrastructure.registry import RegistryClient
from src.ml.features import create_sequences
from src.pipelines.ingest_data import run_ingestion
from src.pipelines.process_data import run_data_processing

logger = setup_logging()


# Função para calcular confiança
def confidence(X, num_runs: int = 10, model=None) -> tuple:
    """
    Roda a predição 'num_runs' vezes ativando o comportamento de treinamento
    (MC Dropout) para gerar variabilidade e medir incerteza.
    """
    # 1. Carrega os artefatos do MLflow apenas se não tiverem sido injetados via parâmetros
    if model is None:
        client = RegistryClient()
        model, scaler, run_id = client.load_model()

    # 2. Executa 10 vezes para gerar um percentual de confiança
    predictions = []
    for _ in range(num_runs):
        # A flag training=True força o Keras a usar o Dropout durante a inferência.
        pred = model(X, training=True).numpy().flatten()  # shape: (n_samples,)
        predictions.append(pred)

    predictions = np.array(predictions)  # Formato: (num_runs, n_amostras)

    # 2. Calcula a Média e o Desvio Padrão (Variabilidade)
    mean_pred = np.mean(predictions, axis=0)  # A predição final oficial
    std_pred = np.std(predictions, axis=0)  # O nível de dúvida do modelo

    # 3. Calcula o Score de Confiança (0 a 100%)
    # Se as previsões variarem mais de 2% (0.02) entre si, a confiança zera. (Rigoroso)
    MAX_TOLERANCE = 0.02

    # Se std_pred for 0 -> (1 - 0) * 100 = 100% de confiança
    # Se std_pred for 0.0061 -> (1 - (0.0061 / 0.02)) * 100 = 69.5% de confiança
    confidence_score = 100 * (1 - (std_pred / MAX_TOLERANCE))

    # Limita entre 0 e 100% para evitar scores negativos se o mercado surtar
    confidence_score = np.clip(confidence_score, a_min=0, a_max=100)

    return mean_pred, std_pred, confidence_score


# Função principal de inferência
def predict(
    ticker: str,
    time_steps: int = 20,
    model=None,
    scaler=None,
    run_id=None,
) -> dict:
    """
    Inferência de ponta a ponta: Dados Gold → sequências em escala → previsões.

    Args:
        ticker:     Símbolo da ação, ex: "JNJ". Deve corresponder ao caminho do arquivo parquet Gold.
        time_steps: Deve ser igual ao valor utilizado durante o treinamento (padrão é 30).
        model:      Opcional — passe um modelo Keras pré-carregado para evitar I/O no MLflow.
        scaler:     Opcional — passe o StandardScaler pré-carregado diretamente.
                    Útil dentro de uma API FastAPI para carregar uma vez na inicialização e reutilizar.

    Returns:
        Um dicionário com as chaves:
            - return_pred: np.ndarray contendo as previsões brutas de Return_Close (saída direta do modelo).
            - price_pred:  np.ndarray contendo as previsões de preço de Fechamento (Close) pós-processadas.
            - dates:       DatetimeIndex alinhado a cada previsão feita.

    Raises:
        ValueError: se o arquivo parquet Gold tiver menos linhas do que o valor de `time_steps`.
    """
    # 1. Pipeline de Dados: Ingestão e Processamento
    # Carrega dados brutos dos últimos 30 dias para o bucket Bronze
    _, parquet_name = run_ingestion(ticker)
    # Processa da camada Bronze para Prata (Silver) e Ouro (Gold) após limpeza e engenharia de features
    df_silver, df_gold = run_data_processing(ticker, parquet_name)

    # 2. Carrega os artefatos do MLflow apenas se não tiverem sido injetados via parâmetros
    if model is None or scaler is None or run_id is None:
        client = RegistryClient()
        model, scaler, run_id = client.load_model()

    # 3. Preparação da Camada Gold — contém apenas features processadas (sem a coluna de preço absoluto Close)
    #    Colunas esperadas: [Return_Close, RSI_15, Dist_EMA_5, Dist_EMA_10, Dist_EMA_15]
    df_gold.set_index("Date", inplace=True)  # type: ignore
    features_array = df_gold.values  # type: ignore # shape: (n_rows, 5)

    if len(features_array) < time_steps:
        logger.info(
            f"Tamanho insuficiente de dados ({len(features_array)}) para o time_steps={time_steps}."
        )
        logger.info("Setando time_steps para o tamanho disponivel")
        time_steps = len(features_array)

    # 4. Busca da âncora na Camada Silver — necessário APENAS para pegar o preço Close real
    #    Isso servirá para converter o "retorno" previsto de volta para "preço".
    close_col = [c for c in df_silver.columns if "Close" in c][0]
    date_col = [c for c in df_silver.columns if "Date" in c][0]
    df_silver = df_silver.set_index(date_col)[close_col]

    # Alinha a coluna Close do Silver com as datas do Gold — protege contra discrepância de contagem de linhas.
    # close_aligned = df_silver.reindex(df_gold.index)

    # 5. Construção de Sequências — espelha exatamente a ordem que foi feita no treinamento.
    #    A variável y_raw = Return_Close (coluna índice 0), que nunca é escalonada no treino.
    #    Cria janelas deslizantes com tamanho igual a `time_steps`.
    X_raw, _ = create_sequences(features_array, time_steps=time_steps)
    # X_raw shape: (n_samples, time_steps, 5)

    # 6. Escalonamento (Normalização) — aplica a mesma transformação matemática do treinamento.
    X = scaler.transform(X_raw.reshape(-1, X_raw.shape[-1])).reshape(X_raw.shape)

    # 7. Predição — a saída é um retorno (Return_Close) e NÃO um preço absoluto.
    # y_pred_return = model.predict(X).flatten()  # shape: (n_samples,)

    mean_pred, std_pred, confidence_score = confidence(X, num_runs=10, model=model)
    std_pred = np.atleast_1d(std_pred)
    confidence_score = np.atleast_1d(confidence_score)

    y_pred_return = np.atleast_1d(mean_pred)

    # 8. Pós-processamento: Convertendo Return_Close → Preço de Fechamento (Close).
    #    A previsão de índice 'k' projeta o Return_Close na linha Gold (k + time_steps).
    #    O preço base (âncora) é o ÚLTIMO dia dessa janela → linha Gold (k + time_steps - 1).
    #    Cálculo: Close_{t} = Close_{t-1} * (1 + Previsão_de_Return_Close)
    pred_dates = df_gold.index[time_steps : time_steps + len(y_pred_return)]  # type: ignore
    anchor_dates = df_gold.index[time_steps - 1 : time_steps - 1 + len(y_pred_return)]  # type: ignore

    # Usa o preço real de fechamento da camada Silver como âncora para o cálculo
    anchor_close = df_silver.loc[anchor_dates].values
    y_pred_price = anchor_close * (1 + y_pred_return)

    # Para logar métricas no futuro
    # client.log_metric(key="prediction_value", value=y_pred_price[-1], run_id=run_id)

    return {
        "return_pred": y_pred_return,  # Saída bruta do modelo (Return_Close)
        "return_std_dev": std_pred,  # Desvio padrão das previsões de retorno
        "confidence_score": confidence_score,  # Nível de confiança da predição (0 a 100)
        "price_pred": y_pred_price,  # Preço de fechamento pós-processado
        "dates": pred_dates,  # Índice de datas alinhado com cada previsão feita
        "model_id": run_id,  # Rastreabilidade de qual modelo gerou o resultado
    }


# Teste rápido via linha de comando (Smoke-test)
# if __name__ == "__main__":
#     from src.infrastructure.registry import RegistryClient
#
#     client = RegistryClient()
#     model, scaler, run_id = client.load_model()
#     result = predict(
#         ticker="JNJ", time_steps=20, model=model, scaler=scaler, run_id=run_id
#     )  # Infere a ação JNJ com janela de 20 dias
#     for key in result.keys():  # Exibe os resultados
#         if key != "model_id":
#             logger.info(f"{key}: {result[key][-1]}")
#         else:
#             logger.info(f"model_id: {result[key]}")
