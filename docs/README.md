# Documentação Técnica e Arquitetural (`docs/`)

Este diretório centraliza toda a documentação teórica, de negócio e técnica sobre a arquitetura, decisões de design e requisitos do projeto **Stock Price Prediction**.

---

## Estrutura de Diretórios

O diretório `docs/` está organizado da seguinte forma:

| Diretório/Arquivo | Descrição Principal |
| :--- | :--- |
| `adr/` | Diretório contendo os *Architectural Decision Records* (ADRs) que documentam as escolhas técnicas cruciais do projeto. |
| `PRD.md` | *Product Requirements Document*. Descreve o escopo do produto, requisitos de dados, objetivos e métricas de sucesso. |
| `architecture.md` | Detalhamento conceitual da arquitetura do sistema, modelagem de dados e integrabilidade das camadas. |
| `repository.md` | Visão geral da organização e governança da base de código do repositório. |

---

## Descrição dos Módulos e Arquivos

### 1. Architectural Decision Records (`adr/`)
Utiliza o formato padronizado pelo template `0000-adr-template.md` para documentar decisões passadas e atuais de engenharia. Alguns registros importantes incluem:
*   `0001-arquitetura-data-lake-s3.md`: Decisão de usar armazenamento compatível com S3 (MinIO/AWS S3) para artefatos e dados Medallion.
*   `0004-otimizacao-de-hiperparametros.md`: Uso do Optuna para sintonia fina de hiperparâmetros da rede LSTM.
*   `0006-escolha-do-ticker-jnj-como-baseline.md`: Escolha de Johnson & Johnson (JNJ) como ativo de baseline.
*   `0009-estrategia-de-calculo-de-score-de-confianca.md`: Estratégia de inferência com MC Dropout para extrair incertezas estatísticas.
*   `0010-Orquestracao-GitHub-Actions.md`: Decisão e trade-offs sobre orquestração usando GitHub Actions.

### 2. Documentação de Escopo e Engenharia
*   **`PRD.md`**: Define o norte do desenvolvimento do Tech Challenge, listando requisitos funcionais (API REST de predição), não-funcionais (tempo de resposta, versionamento de modelos) e especificações do modelo LSTM.
*   **`architecture.md`**: Explica detalhadamente o pipeline Medallion do projeto (Bronze -> Silver -> Gold), bem como a arquitetura de Serving em tempo real para mitigar o viés de *Training-Serving Skew*.

---

## Fluxo de Operação

1.  **Entrada no Projeto**: O novo desenvolvedor deve ler inicialmente o `PRD.md` para entender as necessidades de negócio.
2.  **Visão da Solução**: Consulta-se `architecture.md` para compreender o fluxo físico e lógico dos dados financeiros e dos modelos de predição.
3.  **Histórico Técnico**: Caso haja dúvidas sobre "por que esta ferramenta ou padrão foi escolhido", o desenvolvedor deve navegar pelo diretório `adr/` para consultar o registro histórico das decisões de design.
