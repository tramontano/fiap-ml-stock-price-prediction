# Product Requirements Document (PRD)
## Stock Price Prediction

## 1. Visão do Produto

> **Resumo Executivo**
> O **Stock Price Prediction** é uma solução completa (*end-to-end*) de Machine Learning, desenhada sobre os pilares de MLOps e *Clean Architecture*. O sistema treina, otimiza e serve um modelo de rede neural profunda do tipo Long Short-Term Memory (LSTM) para prever o preço de fechamento de ativos financeiros da bolsa de valores (com caso de uso inicial na ação Johnson & Johnson - JNJ). A plataforma se diferencia por resolver ativamente o problema do *Training-Serving Skew*, recalculando as *features* em tempo real durante a inferência.

**Personas de Usuários:**
*   **Analista Quantitativo (Quant):** Busca sinais numéricos precisos e predições sólidas para compor ou validar suas estratégias algorítmicas de *trading*.
*   **Gestor de Portfólio / Investidor:** Utiliza a previsão da tendência direcional do ativo para rebalancear a carteira de investimentos no melhor *timing*.
*   **Engenheiro de Machine Learning / MLOps:** Focado na manutenibilidade da solução, buscando garantir *pipelines* de treino totalmente reprodutíveis e monitoramento contínuo do ciclo de vida do modelo.

**Proposta de Valor Principal:**
Entregar previsões do mercado financeiro de alta confiabilidade por meio de uma arquitetura resiliente e automatizada. A solução oferece uma API RESTful de alta performance integrada de forma coesa às ferramentas padrão do mercado (MLflow, Apache Airflow, Docker, FastAPI), eliminando a barreira entre o ambiente de experimentação de dados e o ambiente em produção.

---

## 2. Requisitos Funcionais

As funcionalidades estão organizadas pelos seus respectivos módulos arquiteturais.

### Módulo: API de Previsão (Serving)

*   **[Feature 1.1] Endpoint de Inferência (Predict)**
    *   **Descrição:** Rota RESTful (ex: `/predict`) que recebe informações/configurações do usuário e retorna a predição do valor de fechamento (Close) para a próxima janela de tempo.
    *   **Regras de Negócio:**
        *   O modelo LSTM e o *pipeline* de *Feature Engineering* (criado com `scikit-learn`) devem ser carregados globalmente no *lifespan* (`app.state.model` e `app.state.pipeline`) da aplicação para evitar vazamento de memória.
        *   Durante o `POST`, a API deve coletar ativamente os dados em tempo real conectando-se à biblioteca `yfinance`.
        *   Tratar o achatamento de colunas dinâmico caso o Yahoo Finance retorne em estrutura de `MultiIndex`.
        *   Garantir a execução da conversão de variáveis exatamente como no treino: `Return_Close`, `RSI_15`, `Dist_EMA_5`, `Dist_EMA_10` e `Dist_EMA_15`.
    *   **Prioridade:** 🔴 Essencial (*Must-have*)

*   **[Feature 1.2] Status do Sistema e Healthcheck**
    *   **Descrição:** Rota (ex: `/health`) para verificação de disponibilidade operacional do container e modelo.
    *   **Regras de Negócio:** Deve confirmar se o objeto do modelo carregado está em um estado legível. Idealmente, retorna qual o Run ID ou modelo (com *champion alias*) está atualmente instanciado.
    *   **Prioridade:** 🔴 Essencial (*Must-have*)

### Módulo: MLOps e Pipeline de Treino (Data Engineering)

*   **[Feature 2.1] Ingestão e Processamento (Arquitetura Medallion)**
    *   **Descrição:** Rotina para extração de dados históricos do mercado financeiro, validação e aplicação de transformadores customizados em camadas de Data Lake.
    *   **Regras de Negócio:**
        *   **Camada Bronze:** Salvar os dados *raw* (crus) do mercado utilizando o formato Parquet para armazenamento otimizado no MinIO.
        *   **Camada Silver:** Higienização de nulos e seleção de colunas OLHCV (*Open, High, Low, Close, Volume*).
        *   **Camada Gold:** Aplicação de *Custom Transformers* para gerar `DailyReturnTransformer`, `EMATransformer` e `RSITransformer`.
    *   **Prioridade:** 🔴 Essencial (*Must-have*)

*   **[Feature 2.2] Otimização e Treinamento do Modelo (LSTM)**
    *   **Descrição:** *Pipeline* de experimentação contínua que utiliza *Bayesian Optimization* para achar a arquitetura de rede neural mais aderente ao ativo.
    *   **Regras de Negócio:**
        *   Empregar a biblioteca Optuna configurada para pelo menos 50 *trials*.
        *   Registrar no MLflow e DagsHub as hiper-configurações selecionadas.
        *   Garantir que o salvamento do `feature_pipeline` do Scikit-Learn e do `lstm_model` ocorram na mesma "Run Filha" do MLflow para manter paridade.
        *   Aplicar uma injeção explícita (*Monkey Patch* - `keras.__version__ = tf.__version__`) para prevenir *bugs* nativos de compatibilidade Keras/MLflow.
    *   **Prioridade:** 🔴 Essencial (*Must-have*)

*   **[Feature 2.3] Orquestração e Retreinamento**
    *   **Descrição:** Desenvolvimento de automação agendada baseada em Apache Airflow (`retrain_dag.py`).
    *   **Regras de Negócio:** Engatilhar fluxo completo de `Ingestão -> Pre-processamento -> Optuna Tuning -> Registro` periodicamente (ex: fechamento mensal ou decaimento do modelo).
    *   **Prioridade:** 🟡 Importante (*Should-have*)

---

## 3. Requisitos Não Funcionais

> [!IMPORTANT]
> A robustez e disponibilidade do sistema se traduzem pelo cumprimento rigoroso destes critérios técnicos.

*   **Desempenho e Latência:** A rota de predição via FastAPI deve processar tensores de dados velozmente, minimizando *overhead*, excetuando-se apenas a latência de rede necessária para se comunicar com os servidores do Yahoo Finance.
*   **Escalabilidade e Portabilidade:** O ambiente do projeto deve ser conteinerizado (Docker). O manifesto `docker-compose.yml` deve integrar de forma fluida bancos locais de rastreabilidade (PostgreSQL e MinIO para simular AWS S3).
*   **Acessibilidade / UX Dev:** A API REST deve ter documentação automatizada via Swagger UI OpenAPI (`/docs`), contendo o descritivo de cada método, atributos, restrições e modelos de saída esperados.
*   **Segurança e Confiabilidade de Dados:** Prevenção de falhas tipo *TypeMismatch* garantindo validação explícita no *Gateway* da API utilizando `Pydantic` (*Schemas*). A arquitetura deve isolar recursos para prevenir *"Out of Memory"* de requisições sobrepostas.

---

## 4. Jornada do Usuário

Abaixo, detalhamos o fluxo de ponta a ponta desde a perspectiva do profissional integrador ou usuário que consome a Inteligência Artificial:

1.  **Descoberta do Serviço:** O profissional acessa o Swagger da API (`http://localhost:8000/docs`) para descobrir as rotas. Ele compreende que deve interagir enviando um JSON (`PredictRequest`).
2.  **Preparação:** Em seu Jupyter Notebook ou plataforma de automação, prepara o *payload* da requisição incluindo o *ticker* de interesse (ex: "JNJ") e submete via POST.
3.  **Ação no Backend (Invisível ao Usuário):**
    *   O *Schema* do Pydantic valida os tipos de dados enviados.
    *   A API baixa *on-the-fly* os dados de fechamento necessários do mercado usando `yfinance`.
    *   O `scikit-learn` executa o *FeatureSelector* e normaliza dados pelo `StandardScaler`.
    *   O sistema cria o vetor 3D `(batch, time_steps, features)` exigido por LSTMs.
    *   O *array* validado é entregue ao Keras para inferência pelo modelo salvo em memória global.
4.  **Entrega do Valor:** A resposta encapsula o resultado e o retorna em um pacote formatado (JSON) sob o esquema `PredictResponse`.
5.  **Tomada de Decisão:** O analista verifica o valor preditivo, comparando-o a dados atuais. Se previsto de alta/baixa considerável, aciona suas automações de corretora ou dashboards de análise.

---

## 5. Métricas de Sucesso (KPIs)

Para mensurar se o esforço deste produto alcança a expectativa real do Tech Challenge e do Mercado:

*   **Métricas de Qualidade de IA:**
    *   **MAPE (Mean Absolute Percentage Error):** Margem de erro em porcentagem do modelo avaliada em base isolada de teste.
    *   **RMSE (Root Mean Square Error):** Avalia e penaliza erros preditivos aberrantes (*outliers*).
*   **Métricas de Integração / API:**
    *   *Uptime*: Manutenção das instâncias via Docker em rodízio saudável.
    *   Tempo Médio de Resposta da API por requisição finalizada.
*   **Métricas de Qualidade de Código:**
    *   Sucesso nos testes de integração via `pytest`.

---

## 6. Próximos Passos (MVP vs. Versões Futuras)

Para um ciclo de vida ágil, organizamos os entregáveis do que deve ser resolvido imediatamente e a visão técnica de evolução de negócio.

### 🔴 MVP (Foco de Entrega para a Fase 4)
*   **Lógica de Registro Ativa:** Alterar a API para que encontre automaticamente o modelo aprovado pelo seu *Champion Alias* configurado no MLflow, deixando de lado URLs manuais no `.env`.
*   **Preparação de Deploy:** Escrita de um `Dockerfile` otimizado em multicamadas estritamente para a API subir no ambiente de produção.
*   **Automações Finais:** Inclusão do contêiner do *Apache Airflow* no *Docker Compose* e finalização dos *scripts* de *Pytest*.
*   **Apresentação:** Finalizar um `README.md` exaustivo contendo *Makefiles* de *setup* e gravação do Vídeo oficial de Demo do Desafio.

### 🔵 Versões Futuras (V2 e Além)
*   **Arquitetura Multimodal e Alternative Data:** Melhorar significativamente o desempenho integrando o modelo **Hugging Face FinBERT** para consumir *Sentiment Analysis* de notícias de portais financeiros, criando colunas contextuais e mesclando com as variáveis quantitativas e técnicas que já possuímos.
*   **Portabilidade Front-End:** Expor as predições em um painel interativo Web como *Streamlit* ou *Next.js* com gráficos de velas e projeção gráfica estendida.
*   **Agnosticismo de Ticker:** Elevar a capacidade do *pipeline* para suportar treinamento dinâmico com paralelismo, gerando modelos dedicados (ou agnósticos) para vários outros ativos além do "JNJ".
