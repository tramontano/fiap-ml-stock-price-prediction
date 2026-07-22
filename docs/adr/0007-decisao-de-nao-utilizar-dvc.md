# 0007. Decisão de Não Utilizar DVC (Data Version Control)

**Status**: Aceito
**Data**: 2026-06-10

## Contexto

Com o avanço do desenvolvimento do projeto e a necessidade de estruturar o fluxo de MLOps de ponta a ponta, avaliamos a adoção do DVC (Data Version Control) para realizar o versionamento dos dados nas camadas Medallion (Bronze, Silver, Gold). O DVC é o padrão de mercado para versionamento de dados massivos e reprodutibilidade de pipelines de dados. No entanto, sua introdução em um projeto com o escopo atual adiciona ferramentas extras à stack que precisam ser avaliadas sob a ótica de custo de complexidade vs. benefício entregue para a entrega da Fase 4 do Tech Challenge.

## Decisão

Decidimos **não utilizar o DVC** para o versionamento dos dados e artefatos de modelo neste momento, mantendo a seguinte estrutura técnica:
1. **MinIO (S3-compatible) + Particionamento Físico:** Armazenamento das camadas Bronze, Silver e Gold em buckets estruturados no MinIO, identificando execuções de forma lógica no caminho das chaves (ex: `JNJ/19850102_20251230.parquet`).
2. **MLflow Model Registry:** Uso exclusivo do MLflow (via DagsHub) para registrar e versionar o pipeline de transformadores do Scikit-Learn (`feature_pipeline`) e o modelo preditivo (`lstm_model`), além de fazer o rastreamento do `Run ID` vinculando o modelo exato aos parâmetros e métricas obtidas.
3. **yfinance dinâmico no Serving:** A API FastAPI baixa dados recentes do mercado sob demanda diretamente da API do Yahoo Finance para alimentar a inferência, diminuindo a necessidade de ter datasets locais históricos estáticos versionados para o serving.

## Consequências

**Positivas:**
- **Redução da Complexidade Técnica:** Menos uma ferramenta e fluxo de trabalho (autenticação DVC remote, comandos de push/pull) para o time configurar e gerenciar tanto localmente quanto nos agentes de CI/CD (GitHub Actions).
- **Sem Redundância de Artefatos:** Evita ter modelos salvos de forma duplicada no MLflow Model Registry e no DVC Storage.
- **Desenvolvimento Ágil:** Foco na robustez da API e nas rotinas do Apache Airflow e GitHub Actions sem a curva de aprendizado e depuração de conflitos de estado de cache do DVC.

**Negativas:**
- **Perda de Rastreabilidade Bit-a-Bit de Dados históricos de treino:** Não teremos arquivos `.dvc` atrelados ao Git apontando para a foto exata do dataset parquet no exato segundo do treino. Embora saibamos a janela temporal do ticker (ex: de 1985 a 2025), dados históricos antigos no yfinance podem sofrer pequenos ajustes pontuais retroativos devido a splits/dividendos não capturados se o dataset for baixado novamente.
- **Dependência de Particionamento Manual:** O controle de versões de dados na camada Medallion fica sob responsabilidade da convenção de nomes de arquivos no MinIO e do banco de dados do Airflow, em vez de um controle declarativo integrado ao Git via DVC.
