# 0006. Escolha do Ticker JNJ (Johnson & Johnson) como Baseline do Modelo Especialista

## Status

Aceite

## Data

2026-06-08

## Contexto

O projeto adota uma arquitetura de "Modelo Especialista" (One-Model-Per-Series) para as previsões de séries temporais com LSTMs. Para validar a eficácia do *pipeline* ponta a ponta (desde a ingestão na camada Bronze até ao *Serving* na API), é necessário definir um ativo financeiro principal (*ticker*) que sirva como *baseline* oficial de pesquisa e desenvolvimento.

Séries temporais financeiras sofrem frequentemente de *Concept Drift* (mudanças de comportamento do mercado). A escolha do ativo inicial dita a complexidade do treino. Ativos excessivamente voláteis ou muito recentes (ex: *startups* de tecnologia recém-chegadas à bolsa) possuem muito ruído e pouco histórico, o que dificulta a prova de conceito do modelo matemático.

## Decisão

Foi decidido adotar o ticker **JNJ (Johnson & Johnson)** como o ativo padrão para o desenvolvimento, treino e validação da V1 do modelo preditivo.

Os fatores que motivaram esta decisão incluem:

1. **Profundidade Histórica:** A JNJ possui capital aberto há décadas, fornecendo um volume de dados denso e contínuo que ultrapassa os 40 anos, permitindo testes robustos de janelas temporais.
2. **Estabilidade e Comportamento Defensivo:** Sendo uma ação do setor de saúde (*defensive stock*), a JNJ tende a ser mais resiliente a choques macroeconómicos de curto prazo, apresentando tendências de longo prazo mais limpas para a rede LSTM capturar, servindo como um excelente *baseline* estatístico.
3. **Conhecimento de Domínio (*Domain Expertise*):** Existe profundo conhecimento interno sobre o ciclo de negócios, operações e fatores externos que afetam a empresa. Esta familiaridade com a organização facilita imenso a fase de *Feature Engineering* e a validação qualitativa das previsões, garantindo que os resultados matemáticos estão alinhados com o contexto real do negócio.

## Consequências

**Positivas:**

* O extenso volume de dados facilita o alcance da convergência estatística do LSTM.
* A interpretação de anomalias no gráfico de perda (*loss*) e nas previsões será muito mais ágil devido ao conhecimento profundo sobre a empresa.
* Redução de ruído aleatório no treino em comparação com ativos de alta volatilidade.

**Negativas / Pontos de Atenção:**

* O modelo treinado com os hiperparâmetros otimizados para a JNJ (estável/defensiva) não deverá ser utilizado diretamente (em *transfer learning* cego) para ativos de comportamento radicalmente diferente (ex: criptomoedas ou ações de tecnologia hiper-voláteis), exigindo que a *pipeline* do Optuna seja executada novamente caso o *ticker* alvo seja alterado no futuro.
