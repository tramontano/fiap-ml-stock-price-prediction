# 0002. Utilização do uv como Gerenciador de Pacotes Python

**Status**: Aceito
**Data**: 2026-06-06

## Contexto

O projeto requer um gerenciamento robusto de dependências para garantir que o ambiente de treinamento local (Docker) seja idêntico ao ambiente de produção (AWS ECS Fargate). Historicamente, pip com requirements.txt não trava sub-dependências adequadamente. Avaliamos o Poetry (padrão de mercado atual) e o uv (ferramenta escrita em Rust, focada em performance). Como os pacotes de Machine Learning (Pandas, Scikit-learn, PyTorch/TensorFlow) costumam ser pesados, o tempo de build em pipelines de CI/CD (GitHub Actions) pode se tornar um gargalo financeiro e de produtividade.

## Decisão

Decidimos adotar o uv como nosso gerenciador de pacotes e ambientes virtuais, em substituição ao pip padrão ou Poetry.

## Consequências

**Positivas**:

- **Velocidade**: Redução drástica no tempo de resolução de dependências e instalação de pacotes, agilizando os builds da imagem Docker no CI/CD.
- **Reprodutibilidade**: Geração de um arquivo de lock determinístico (uv.lock), garantindo paridade total entre desenvolvimento e produção.
- **Simplicidade**: O uv respeita o padrão pyproject.toml sem exigir configurações excessivamente opinativas.

**Negativas**:

- **Curva de adoção**: Por ser uma ferramenta mais recente no ecossistema, novos contribuidores (ou avaliadores) podem não ter familiaridade imediata com os comandos do uv em comparação ao clássico pip. (Mitigação: comandos serão encapsulados no arquivo Makefile).
