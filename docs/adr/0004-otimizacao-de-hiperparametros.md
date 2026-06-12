# 0004. Utilização do Optuna para Otimização de Hiperparâmetros

**Status**: Aceito
**Data**: 2026-06-06

## Contexto

Para o ajuste fino de nossos modelos, a abordagem tradicional baseada em busca exaustiva (GridSearchCV) ou amostragem aleatória (RandomizedSearchCV) do scikit-learn tem se mostrado ineficiente. Dada a natureza do nosso projeto, que envolve modelos de Deep Learning com alto custo computacional, testar todas as combinações de hiperparâmetros por força bruta é proibitivo em termos de tempo e custo de processamento. Precisamos de uma solução que explore o espaço de busca de forma inteligente, convergindo mais rápido para resultados ótimos sem a necessidade de uma exaustão completa do espaço de parâmetros.

## Decisão

Decidimos adotar o Optuna como nossa ferramenta padrão para otimização de hiperparâmetros (Hyperparameter Tuning).

## Consequências

**Positivas**:

- **Eficiência Algorítmica**: O uso de Otimização Bayesiana permite que o sistema "aprenda" com tentativas anteriores. O Optuna descarta regiões do espaço de busca com baixo potencial de performance e concentra o poder computacional nas combinações mais promissoras.
- **Produtividade**: Redução significativa no tempo necessário para encontrar hiperparâmetros que minimizem a função de perda, acelerando o ciclo de experimentação.
- **Flexibilidade**: Facilidade de integração com diferentes frameworks (PyTorch, TensorFlow, Scikit-learn), permitindo otimizar desde a taxa de aprendizado até a arquitetura da rede (número de unidades, camadas e estratégias de regularização como dropout).

**Negativas**:

- **Complexidade de Configuração**: Requer a definição de um *objective function* para o Optuna, o que adiciona um nível extra de abstração ao código de treinamento, diferindo dos métodos clássicos do scikit-learn.
- **Gerenciamento de Estado**: Como o Optuna realiza múltiplas iterações (*trials*), é necessário garantir que cada trial seja isolado e que os melhores resultados sejam devidamente logados no DagsHub (conforme definido no ADR 0003) para evitar perda de histórico de experimentos.
