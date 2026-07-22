# 0008. Estratégia de Monitoramento e Observabilidade com Prometheus e OpenTelemetry

**Status**: Aceito
**Data**: 2026-06-10

## Contexto

Para atender ao requisito de monitoramento do Tech Challenge Fase 4 ("rastrear a performance do modelo em produção, incluindo tempo de resposta e utilização de recursos"), precisamos de uma estratégia que seja testável no ambiente de desenvolvimento local (Docker Compose) e facilmente portável/compatível com um deploy em produção na nuvem (AWS ECS Fargate ou App Runner), sem alterar a base de código do sistema.

## Decisão

Adotaremos a **Solução baseada no Padrão Prometheus (OpenMetrics)**:
1. **Instrumentação da API:** Integraremos a biblioteca `prometheus-fastapi-instrumentator` no FastAPI para coletar automaticamente e expor métricas na rota `/metrics`.
2. **Ambiente Local (Docker Compose):** Subiremos um container de **Prometheus** (para coletar/scraping métricas de latência e saúde da API) e um container do **cAdvisor** (para coletar uso de recursos físicos CPU/RAM dos containers docker ativos), centralizando os dados em um dashboard customizado no **Grafana**.
3. **Ambiente AWS (Produção):** A API continuará expondo o endpoint `/metrics` da mesma forma. A coleta e redirecionamento de métricas serão feitos de forma transparente e gerenciada pela nuvem através de um container *sidecar* do **AWS Distro for OpenTelemetry (ADOT)** ou AWS ECS Collector, que raspa o endpoint `/metrics` e envia as informações de tempo de resposta e uso de recursos físicos para o **Amazon CloudWatch Metrics** ou **Amazon Managed Service for Prometheus**.

## Consequências

**Positivas:**
- **Paridade Absoluta:** O código da API permanece 100% idêntico entre o ambiente local e a produção AWS.
- **Portabilidade:** A rota `/metrics` é compatível com qualquer ferramenta de observabilidade moderna do mercado (Datadog, New Relic, Grafana Cloud, CloudWatch).
- **Sem Sobrecarga de Performance:** A API apenas computa e expõe as métricas de forma assíncrona na memória RAM na rota `/metrics`. O scraping de dados é feito de fora para dentro, não adicionando latência de requisições de rede síncronas na rota de inferência `/predict`.

**Negativas:**
- **Uso adicional de memória/processamento no container:** A biblioteca de instrumentação utiliza uma pequena fração de recursos adicionais para armazenar os contadores e histogramas das chamadas na memória do container da API FastAPI.
