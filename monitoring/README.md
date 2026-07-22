# Observabilidade e Monitoramento (`monitoring/`)

Este diretório armazena todos os arquivos de configuração de monitoramento e observabilidade em tempo real para o serviço de predição de preços de ações. A stack de monitoramento é composta por Prometheus e Grafana.

---

## Estrutura de Diretórios

O diretório `monitoring/` está estruturado da seguinte forma:

| Diretório/Arquivo | Descrição Principal |
| :--- | :--- |
| `grafana/` | Configurações de provisionamento de *dashboards* e *datasources* do Grafana. |
| `prometheus/` | Configurações de coleta de métricas (scraping) do Prometheus. |

---

## Descrição dos Módulos e Arquivos

### 1. Grafana (`grafana/`)
*   **`provisioning/`**: Contém subpastas que definem a configuração automática do Grafana ao inicializar:
    *   `datasources/`: Configura o Prometheus local como fonte de dados padrão.
    *   `dashboards/`: Contém arquivos JSON de definição dos painéis visuais para monitorar latência de requisições, status HTTP, taxa de erros da API e estatísticas de predição de preços.

### 2. Prometheus (`prometheus/`)
*   **`prometheus.yml`**: Define o comportamento de coleta do Prometheus. Especifica a frequência de amostragem (ex: 15s) e o *target* (alvo) da coleta, que aponta diretamente para o endpoint de métricas exposto pela API FastAPI (normalmente rodando na porta `8000` em `/metrics`).

---

## Fluxo de Operação

1.  **Exposição de Métricas**: A API FastAPI (configurada em `src/api/main.py`) exporta métricas de sistema e de negócio através da biblioteca integrada do Prometheus.
2.  **Coleta (Scraping)**: O contêiner do Prometheus lê o arquivo `prometheus/prometheus.yml`, identifica o endereço da API e faz requisições periódicas a `/metrics`, persistindo os dados temporalmente.
3.  **Visualização**: O Grafana inicia, lê as configurações de provisionamento locais e renderiza os gráficos em tempo real utilizando os dados expostos pelo Prometheus, permitindo que a equipe de MLOps acompanhe o estado de saúde do sistema de serving.
