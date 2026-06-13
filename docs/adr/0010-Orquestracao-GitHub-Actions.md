# 0010. Escolha de Orquestração e Background Tasks (GitHub Actions vs Celery vs Airflow)

**Data:** 2026-06-13
**Status:** Aceite

## 1. Contexto e Problema

O projeto atual (Previsão de Ativos Financeiros com LSTM) requer a execução de tarefas fora do ciclo de vida síncrono da API FastAPI. Especificamente, precisamos de:
1. Ingestão periódica de dados históricos (Data Lake Bronze/Silver).
2. Retreino periódico do modelo LSTM com otimização Bayesiana (Optuna) para evitar degradação de performance (Model Drift).

Foram avaliadas três abordagens para orquestração e execução destas tarefas:
- **GitHub Actions:** Ferramenta de CI/CD com suporte a agendamento via *cron*.
- **Celery + Redis:** Fila de tarefas distribuídas (Message Broker) nativa do ecossistema Python.
- **Apache Airflow (MWAA / DIY ECS):** Plataforma padrão da indústria para criação de fluxos de trabalho (DAGs) complexos.

O desafio reside em equilibrar a complexidade operacional, o custo da infraestrutura AWS e a necessidade real de processamento do estágio atual do projeto.

## 2. Decisão

**Decidimos adotar o GitHub Actions como a ferramenta principal para orquestração de pipelines e *cron jobs* nesta fase do projeto.**

Descartamos temporariamente o Celery+Redis e o Apache Airflow pelas seguintes razões:
- A nossa API FastAPI atualmente não possui rotas que acionam processamento assíncrono pesado gerado por interação do utilizador final. A inferência é síncrona e rápida. Logo, a complexidade de manter um *broker* (Redis) e *workers* (Celery) não se justifica (Overengineering).
- O fluxo de retreino é linear (Extração -> Transformação -> Treino -> Registo) e não excede o tempo limite de 6 horas das instâncias do GitHub.
- A implementação do Airflow (seja AWS MWAA ou ECS DIY) adicionaria um custo mensal significativo (entre $60 e $350+) à infraestrutura base, o que é desproporcional para o orçamento da conta de estudante da FIAP.

O GitHub Actions resolve o problema de agendamento de forma gratuita, escalável (para workloads de curta duração) e mantém o código de infraestrutura limpo.

## 3. Consequências

**Positivas:**
- Custo de orquestração reduzido a zero ($0/mês).
- Menor carga cognitiva e operacional (não há bases de dados de metadados ou *workers* para manter e monitorizar).
- Centralização da lógica de CI/CD e orquestração de dados na mesma ferramenta.

**Negativas:**
- Lógica de falha e *retry* limitadas. O GitHub Actions não é ideal para recuperar pipelines no meio de uma execução (ex: se o passo 3 de 5 falhar, é complexo reiniciar apenas do passo 3).
- Acoplamento da orquestração de dados à plataforma de alojamento de código-fonte.
- Dificuldade na visualização gráfica do pipeline de dados (não há interface equivalente à UI rica do Airflow para DAGs).

## 4. Próximos Passos (Caminho de Evolução)

À medida que o projeto ganhar complexidade e novos requisitos surgirem, adotaremos o seguinte caminho de evolução arquitetural:

1. **Fase Atual (GitHub Actions):** Orquestração de tarefas lineares, retreino agendado e ingestão de *batch* diária.
2. **Evolução 1 (Celery + Redis + Flower):** A adotar assim que a API FastAPI necessitar de processar tarefas assíncronas iniciadas pelo utilizador (ex: *"Gerar relatório analítico de 10 anos"* ou *"Treinar modelo personalizado sob demanda"*). Necessário para evitar *timeouts* do Load Balancer e libertar *threads* do Uvicorn.
3. **Evolução 2 (Apache Airflow - DIY ECS):** A adotar quando o pipeline de dados deixar de ser linear e se tornar um grafo direcionado acíclico (DAG) com dependências complexas (ex: múltiplos *crawlers* paralelos de Alternative Data, agregação de dezenas de *tickers*, *backfilling* de dados históricos).
4. **Evolução 3 (AWS MWAA):** A adotar apenas num cenário de larga escala empresarial, onde o custo de engenharia para manter a infraestrutura manual do Airflow (Fargate + RDS + Redis) ultrapasse o custo do serviço gerido da AWS (~$350/mês), exigindo alta confiabilidade e SLAs corporativos.
