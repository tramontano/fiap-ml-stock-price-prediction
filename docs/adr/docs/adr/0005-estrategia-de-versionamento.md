# 0005. Estratégia de Versionamento e Tags: Champion vs Challenger

**Status**: Aceito
**Data**: 2026-06-06

## Contexto

Com a adoção do DagsHub como nosso Model Registry, precisamos estabelecer um protocolo rigoroso para identificar o status de prontidão de cada modelo. Sem uma convenção clara, corremos o risco de implantar modelos experimentais ou não validados em produção. É necessário definir uma nomenclatura que permita ao time e às nossas esteiras de CI/CD distinguir entre modelos que estão em fase de teste (Challenger) e o modelo que está validado e aprovado para servir o tráfego real (Champion).

## Decisão

Adotaremos a estratégia de *Model Aliasing* (apelidos) no DagsHub/MLflow para gerenciar o status dos artefatos:

1. **Champion**: O modelo em produção, considerado o estado-da-arte, utilizado por todas as requisições de inferência.
2. **Challenger**: O modelo candidato, que obteve métricas superiores em experimentos recentes e está em processo de validação (A/B testing ou shadow deployment).
3. **Experimental**: Qualquer versão que não possua um dos apelidos acima.

A transição será gerida através do GitHub Actions: sempre que um *Pull Request* no repositório de modelos é mesclado para a branch `main`, a CI deve automaticamente aplicar a tag de *Challenger* à versão correspondente no DagsHub. A promoção de *Challenger* para *Champion* será realizada manualmente ou via aprovação de um *Release* no GitHub.

## Consequências

**Positivas**:

- **Governança**: Evita deploy acidental de modelos experimentais, garantindo que o ambiente AWS busque apenas o modelo apontado pela tag `champion`.
- **Rastreabilidade**: Facilita a reversão (*rollback*). Caso o *Champion* apresente problemas, o sistema pode apontar instantaneamente para o *Challenger* (ou o *Champion* anterior) via alteração de aliasing no DagsHub.
- **Transparência**: Permite que qualquer membro do time visualize claramente o progresso dos modelos dentro da interface do DagsHub.

**Negativas**:

- **Gestão de Mudanças**: Requer disciplina na atualização dos aliases. Se o time esquecer de promover um *Challenger* após a validação, a aplicação continuará servindo o modelo anterior. (Mitigação: Automação via pipeline que notifica o time quando um *Challenger* performa consistentemente acima do *Champion* atual).
- **Complexidade de Pipeline**: Adiciona uma etapa de chamada de API ao DagsHub dentro das nossas esteiras de CI/CD para atualizar os *aliases* após cada treino bem-sucedido.
