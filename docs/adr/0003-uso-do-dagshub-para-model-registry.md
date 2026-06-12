# 0003. Uso do DagsHub como Model Registry

**Status**: Aceito
**Data**: 2026-06-06

## Contexto

À medida que iteramos sobre nossos modelos de Machine Learning, surge a necessidade de rastrear métricas, versionar artefatos e gerenciar ativamente o ciclo de vida dos modelos. É um requisito fundamental que, tanto no ambiente AWS (produção/deploy) quanto no ambiente local de testes (desenvolvimento), exista uma fonte única de verdade (*single source of truth*) para realizar o pull do modelo *champion* e rodar as predições e testes. Sem um registro centralizado, corremos o grave risco de dessincronização de artefatos entre desenvolvedores e o servidor de produção. Avaliamos subir uma instância própria do MLflow na AWS, mas isso adicionaria complexidade de infraestrutura (banco de dados, bucket S3, servidor EC2/ECS) e custos operacionais que não são justificados nesta fase do projeto.

## Decisão

Decidimos adotar o DagsHub (através de sua integração remota e gerenciada com o MLflow) como nosso Model Registry e rastreador de experimentos padrão.

## Consequências

**Positivas**:

- **Fonte Única de Verdade**: Garante que qualquer ambiente (pipeline de CI/CD, AWS ECS ou máquina local) faça o download da exata mesma versão do modelo *champion* para inferência e testes.
- **Zero Overhead de Infraestrutura**: Eliminamos a necessidade de provisionar, manter e configurar credenciais de servidores próprios para o MLflow, focando apenas no desenvolvimento do modelo.
- **Facilidade de Integração**: O DagsHub fornece URIs de rastreamento prontas que se integram de forma transparente com a biblioteca padrão do `mlflow` no Python via variáveis de ambiente.

**Negativas**:

- **Dependência de Terceiros (SaaS)**: A arquitetura passa a depender da disponibilidade do DagsHub. Se a plataforma apresentar instabilidade, pipelines de CI/CD que tentem fazer o pull do modelo para deploy na AWS podem falhar.
- **Latência de Rede**: Ao contrário de um artefato salvo em um bucket S3 na mesma região da nossa infraestrutura AWS, o download do modelo via DagsHub pode apresentar uma latência ligeiramente maior durante o cold start das aplicações. (Mitigação: embutir o modelo na imagem Docker durante o build da esteira de CI/CD, em vez de baixá-lo em tempo de execução).
