# Suíte de Testes Automatizados (`tests/`)

Este diretório contém os testes automatizados da aplicação **Stock Price Prediction**, estruturados sob o framework `pytest` para garantir a corretude das rotinas de engenharia de dados, transformadores de ML, esquemas de validação e endpoints de serviço.

---

## Estrutura de Diretórios

O diretório `tests/` está organizado da seguinte forma:

| Diretório/Arquivo | Descrição Principal |
| :--- | :--- |
| `unit/` | Testes unitários focados na validação isolada de módulos, com uso extensivo de *mocks*. |
| `integration/` | Testes de integração que verificam a comunicação conjunta de componentes e endpoints da API. |
| `__init__.py` | Arquivo de inicialização do módulo de testes. |

---

## Descrição dos Módulos e Arquivos

### 1. Testes Unitários (`unit/`)
*   **`test_transformers.py`**: Valida a lógica de cálculo dos transformadores de engenharia de *features* (`RSITransformer`, `EMATransformer`, `DailyReturnTransformer`).
*   **`test_storage_client.py`**: Testa as operações de leitura/escrita e manipulação de arquivos Parquet no MinIO/S3 utilizando mocks.
*   **`test_ingest_data.py`**: Garante que o download e armazenamento dos dados brutos a partir da API `yfinance` funcione corretamente.
*   **`test_schemas.py`**: Verifica as regras de validação e conformidade dos esquemas Pydantic (`PredictRequest`, `PredictResponse`).
*   **`test_features.py`** e **`test_tune_pipeline_utils.py`**: Validam funções auxiliares de pré-processamento de séries temporais e geração de janelas 3D para o modelo LSTM.

### 2. Testes de Integração (`integration/`)
*   **`test_api.py`**: Realiza chamadas simuladas aos endpoints da API FastAPI (`/health` e `/predict`) utilizando o `TestClient` do FastAPI, validando o ciclo de vida completo da requisição e respostas.
*   **`test_mlflow_auth.py`**: Garante que a integração e autenticação com o servidor MLflow/DagsHub esteja respondendo adequadamente para download/upload de artefatos.

---

## Fluxo de Operação

1.  **Instalação**: Garanta que as dependências de desenvolvimento do `pytest` estejam instaladas (definidas no `pyproject.toml`).
2.  **Execução Completa**:
    *   Para rodar todos os testes do projeto, execute o comando na raiz:
        ```bash
        pytest
        ```
    *   O pytest lê a configuração básica contida no arquivo `pytest.toml` na raiz do projeto, descobre os testes nas pastas `unit/` e `integration/` e apresenta o relatório de passagem.
3.  **CI/CD**: Estes testes são executados automaticamente a cada pull request ou push em branches protegidas no workflow de CI para assegurar que nenhuma modificação quebre funcionalidades essenciais do ecossistema.
