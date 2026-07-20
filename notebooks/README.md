# Notebooks Interativos (`notebooks/`)

Este diretório é dedicado ao armazenamento de notebooks Jupyter usados para análise exploratória de dados (EDA), experimentação rápida de algoritmos, prototipagem de engenharia de *features* e visualização de dados do mercado financeiro.

---

## Estrutura de Diretórios

O diretório `notebooks/` está organizado da seguinte forma:

| Arquivo | Descrição Principal |
| :--- | :--- |
| `01_exploracao_yfinance.ipynb` | Jupyter Notebook focado na análise exploratória inicial dos dados históricos extraídos via Yahoo Finance (`yfinance`). |

---

## Descrição dos Módulos e Arquivos

### 1. Exploração do Yahoo Finance (`01_exploracao_yfinance.ipynb`)
Este notebook serve como o primeiro passo investigativo no ciclo de desenvolvimento de machine learning do projeto. Ele aborda:
*   Conexão interativa com a API do Yahoo Finance para extração de ativos (utilizando o *ticker* de baseline `JNJ`).
*   Inspeção e limpeza primária dos dados (verificação de nulos, inconsistências e tipo de dados).
*   Visualização gráfica do comportamento dos preços históricos de fechamento (Close), volume e volatilidade.
*   Protótipos de engenharia de *features* estacionárias para posterior alimentação das redes neurais LSTM.

---

## Fluxo de Operação

1.  **Instalação de Dependências**: Certifique-se de que os pacotes de visualização e manipulação (como `matplotlib`, `seaborn`, `pandas` e `yfinance`) estejam instalados no ambiente virtual (gerenciado pelo `uv`).
2.  **Execução Interativa**: Execute o Jupyter Server localmente ou através da extensão do VS Code para rodar as células do notebook sequencialmente.
3.  **Transição para Código de Produção**: Os insights, limpezas testadas e visualizações validadas neste ambiente interativo são consolidados e transpostos para os scripts estruturados e modulares localizados em `src/pipelines/` e `src/ml/`.
