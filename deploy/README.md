# Infraestrutura e Implantação (`deploy/`)

Este diretório contém todas as definições e configurações para infraestrutura e implantação da aplicação **Stock Price Prediction**, englobando tanto o empacotamento com Docker quanto o provisionamento na nuvem AWS via Terraform.

---

## Estrutura de Diretórios

O diretório `deploy/` está organizado da seguinte forma:

| Diretório | Descrição Principal |
| :--- | :--- |
| `docker/` | Contém as definições de ambiente virtualizado (Dockerfile) para servir a API de previsão. |
| `terraform/` | Contém as definições de Infraestrutura como Código (IaC) para provisionamento de recursos AWS. |

---

## Descrição dos Módulos e Arquivos

### 1. Docker (`docker/`)
*   **`Dockerfile`**: Configuração de construção de imagem Docker multi-stage otimizada. Utiliza o gerenciador de pacotes rápido `uv` e uma imagem base `python:3.11-slim` para gerar uma imagem leve e segura para o serviço da API FastAPI em ambiente produtivo.

### 2. Terraform (`terraform/`)
*   **`environments/`**: Diretórios de ambiente contendo arquivos de definição de variáveis (`terraform.tfvars`) e chamada dos módulos principais para isolamento de ambientes (`dev` e `prod`).
*   **`modules/`**: Componentes de infraestrutura reutilizáveis:
    *   `networking/`: Configuração de VPC, Subnets, Route Tables e Security Groups.
    *   `storage/`: Buckets S3 para armazenar dados e artefatos de modelos.
    *   `iam/`: Políticas e Roles de acesso com privilégio mínimo.
    *   `compute/`: Instâncias EC2 ou serviços de container para hospedar a API.
*   **`README.md`**: Guia passo a passo de como planejar e aplicar as definições de infraestrutura reais na AWS.
*   **`README-LocalStack.md`**: Manual detalhado para testes de infraestrutura local simulada através do LocalStack e `tflocal`.

---

## Fluxo de Operação

1.  **Testes de Infraestrutura Local (LocalStack)**:
    *   Inicia-se o contêiner LocalStack via `docker-compose`.
    *   Executam-se os testes do Terraform apontando para o endpoint local por meio da ferramenta `tflocal` para validar políticas e provisionamento local de S3.
2.  **Preparação e Build da Imagem**:
    *   A API é empacotada a partir do `deploy/docker/Dockerfile`.
    *   A imagem construída é enviada para o registro de contêineres (ECR).
3.  **Provisionamento Cloud**:
    *   Define-se o ambiente de destino (`deploy/terraform/environments/dev` ou `prod`).
    *   Executam-se os comandos do Terraform (`init`, `plan`, `apply`) para provisionar os recursos na nuvem de forma controlada.
