# Infraestrutura e Implantação (`deploy/`)

Este diretório contém todas as definições e configurações para infraestrutura e implantação da aplicação **Stock Price Prediction**, englobando tanto o empacotamento com Docker.

---

## Estrutura de Diretórios

O diretório `deploy/` está organizado da seguinte forma:

| Diretório | Descrição Principal |
| :--- | :--- |
| `docker/` | Contém as definições de ambiente virtualizado (Dockerfile) para servir a API de previsão. |

---

## Descrição dos Módulos e Arquivos

### Docker (`docker/`)

*   **`Dockerfile`**: Configuração de construção de imagem Docker multi-stage otimizada. Utiliza o gerenciador de pacotes rápido `uv` e uma imagem base `python:3.11-slim` para gerar uma imagem leve e segura para o serviço da API FastAPI em ambiente produtivo.
