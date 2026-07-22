# 🗺️ TODO e Próximos Passos (Roadmap)

## ☁️ Orquestração, Infraestrutura e Deploy (Fase 4 Atual)

* [x] **Artefatos e MLflow:** Implementar a lógica de busca do modelo usando o alias `champion` via MLflow Client (eliminando a necessidade de `.env` manual na API).
* [x] **Dockerização:** Criar `Dockerfile.api` focado em produção (Multi-stage build usando `uv` e imagem `python-slim`).
* [x] **Observabilidade:** Adicionar métricas padrão do Prometheus e criar Dashboards no Grafana.
* [x] **Orquestração (Airflow):** Adicionar as DAGs (`airflow_pipeline_dag.py`) compatíveis com Airflow 3.3.0 para orquestrar ingestão, processamento e retreino.
* [x] **Orquestração (CI/CD):** Criar workflow alternativo e leve no GitHub Actions (`retrain.yml`) para pipeline de dados com custo zero.
* [x] **Infraestrutura como Código (IaC):** Desenvolver todo o projeto Terraform (`deploy/terraform/`) usando módulos (Networking, Storage, ECR, IAM, Compute) e separação de ambientes (`dev` e `prod`).
* [x] **Testes Locais AWS:** Integrar o **LocalStack** no `docker-compose.yml` e escrever o guia de testes locais com o Terraform (`tflocal`).
* [x] **Documentação Arquitetural:** Escrever ADRs críticas:
  * ADR 0009: Estratégia de Cálculo do Score de Confiança na Inferência (Monte Carlo Dropout e Tolerância Máxima).
  * ADR 0010: Escolha de Orquestração e Background Tasks (GitHub Actions vs Celery vs Airflow).
* [x] **Qualidade de Código:** Adicionar testes de integração (Pytest) na pasta `tests/integration/` para garantir a resposta correta da API FastAPI simulando dependências reais.

---

## 🏁 Entrega Final (Tech Challenge)

* [ ] **Documentação:** Preencher o `README.md` raiz com instruções claras de execução, arquitetura geral e atalhos de execução (`Makefile`).
* [x] **Documentação:** Criar `README.md` em todas as pastas da raiz do projeto (deploy, docs, monitoring, notebooks, tasks, tests) conforme as regras do GEMINI.md.
* [ ] **Apresentação:** Gravar o vídeo demonstrando a arquitetura, requisições na API, visualização de logs/métricas e pipeline de orquestração.

---

## 🚀 V2 Futura (Arquitetura Multimodal)

* [ ] **Alternative Data:** Enriquecer o modelo integrando análise de sentimento de notícias do mercado financeiro. Utilizar o modelo Hugging Face FinBERT para processar as notícias e juntar esses *scores* com as features temporais já existentes.
