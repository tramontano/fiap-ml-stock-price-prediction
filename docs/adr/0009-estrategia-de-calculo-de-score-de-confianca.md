# Título: 0009 - Estratégia de Cálculo do Score de Confiança na Inferência (Monte Carlo Dropout e Tolerância Máxima).

**Status**: Aceito
**Data**: 2026-06-11

## Contexto

Ao implementar a API de inferência, percebeu-se a necessidade de calcular o Score de Confiança na inferência, ou seja, precisamos saber o quanto podemos confiar na predição feita pelo modelo. Para isso, foi necessário implementar uma estratégia de cálculo do Score de Confiança na inferência, que leva em consideração o comportamento do modelo durante o treinamento (Monte Carlo Dropout e Tolerância Máxima).

## Decisão

Optamos por consolidar o uso do Monte Carlo Dropout (training=True durante a inferência) como mecanismo de aproximação Bayesiana para capturar a incerteza epistêmica do modelo, realizando 10 rodadas (passes diretos) por inferência para calcular a variabilidade (Desvio Padrão).

Contudo, para o cálculo do Score de Confiança (0% a 100%), optamos por abandonar a fórmula do Coeficiente de Variação. No seu lugar, implementamos o método de Tolerância Máxima de Desvio Padrão. Definimos uma constante (ex: MAX_TOLERANCE = 0.02 ou 2%) que representa o limite máximo de risco aceitável. O score é calculado da seguinte forma: Se as previsões variarem mais que MAX_TOLERANCE, a tolerância máxima, (exemplo: 2% ou 0.02) entre si, a confiança zera: Score = 100 * (1 - (std_pred / MAX_TOLERANCE)).

## Consequências

**Ganhos (Prós)**:

* Gestão de Risco: O score agora reflete com precisão a confiança da rede com base em limites de risco de mercado reais, ignorando o problema matemático de médias próximas a zero.

* Maturidade: O uso de MC Dropout para estimação de incerteza previne decisões cegamente automatizadas baseadas em "chutes" da rede neural.

* Observabilidade: Fornece uma métrica contínua (confidence_score) que servirá de alarme natural para degradação do modelo (Model Drift).

**Custos/Impactos Negativos (Contras)**:

* Aumento na Latência de Inferência: Exigir 10 rodadas de predição em vez de uma torna a etapa de inferência ligeiramente mais lenta (saindo de ~500ms para ~750ms).

* Manutenção de Hiperparâmetros de Negócio: A constante MAX_TOLERANCE passa a ser um parâmetro que exige manutenção e tuning manual, dependendo diretamente da volatilidade histórica do ativo analisado (ações mais voláteis exigirão limites de tolerância maiores).

## Comentários

**Aumento na Latência de Inferência**: A diferença de tempo não cresce de forma linear (de 500ms para 5000ms) devido ao custo do *Warmup* (Aquecimento).

A primeira inferência "paga o pedágio" de todo o setup inicial. Nela, o sistema perde milissegundos preciosos fazendo a alocação inicial de variáveis (*Memory System Stabilization*), carregando os pesos da rede neural para o cache do processador (*Cache Priming*) e compilando operações matemáticas complexas em tempo de execução (*Just-In-Time* Compilation - JIT Compilation).

Assim que essa primeira execução termina, o ambiente já está "quente" e estabilizado. Essa característica é muito conhecida em sistemas de benchmarking e também é conhecido como *cold start* quando se fala de latencia de execuções Lambda na AWS após um período de inatividade.