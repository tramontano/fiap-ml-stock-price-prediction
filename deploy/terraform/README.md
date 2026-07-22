# Infrastructure as Code (Terraform)

Este diretório contém a infraestrutura como código (IaC) necessária para fazer o deploy completo da API de Previsão de Ações na AWS. O projeto adota uma abordagem modular e separação de ambientes, alinhada com as melhores práticas de Engenharia de MLOps e DevOps.

---

## Arquitetura na Nuvem

A arquitetura provisiona um ambiente escalável e seguro para servir modelos de Machine Learning (Inference API):

- **Networking:** VPC própria, Subnets Públicas (ALB) e Privadas (ECS), com NAT Gateway para saída segura.
- **Compute (Serving):** ECS com Fargate (Serverless Container), recebendo tráfego balanceado por um Application Load Balancer (ALB). Auto Scaling baseado no uso de CPU.
- **Storage (Data Lake & Model Registry):** Buckets S3 divididos nas camadas Medallion (`bronze`, `silver`, `gold`) e um bucket dedicado e versionado para artefatos de modelos (`models`).
- **ECR:** Repositório Docker privado com verificação de vulnerabilidades (Scan on Push).
- **IAM:** Princípio do menor privilégio. A API pode ler modelos e acessar dados, mas não pode destruir infraestrutura ou acessar a outros serviços não autorizados.

---

## Estrutura do Diretório

A infraestrutura está dividida em duas grandes categorias: **Módulos** (Fábrica de componentes) e **Ambientes** (Onde os componentes são montados).

```text
deploy/terraform/
├── modules/                      # Blocos de infraestrutura reutilizáveis e genéricos
│   ├── compute/                  # ECS Fargate, ALB, Target Groups e Auto Scaling
│   ├── ecr/                      # Elastic Container Registry (Repositórios Docker)
│   ├── iam/                      # Perfis de Segurança (Task Role e Execution Role)
│   ├── networking/               # VPC, Subnets Públicas/Privadas, NAT Gateway e Security Groups
│   └── storage/                  # Buckets S3 (Data Lake e Artefatos), Encriptação e Lifecycle
│
└── environments/                 # Instanciação dos módulos com configurações específicas
    ├── dev/                      # Ambiente de Desenvolvimento / Validação
    └── prod/                     # Ambiente de Produção (Alta Disponibilidade)
```

---

## Módulos (`modules/`)

Os módulos são genéricos e não possuem estado. Eles apenas aceitam variáveis e retornam recursos.

* **`networking/`**: Cria a fundação da rede. Garante que os containers (ECS) correm numa subnet privada, invisíveis à Internet, enquanto o Load Balancer recebe os pedidos HTTP/HTTPS na subnet pública.
* **`storage/`**: Onde os dados e modelos residem. Configura transições automáticas para Glacier (redução de custos) e versionamento de modelos para permitir rollback imediato.
* **`ecr/`**: O destino final do pipeline CI/CD. Armazena as imagens Docker da API e valida se existem vulnerabilidades no código antes de cada deploy.
* **`compute/`**: O motor do sistema. Atrela a imagem Docker a recursos de CPU/RAM, levanta a API com Uvicorn e expõe métricas para o CloudWatch.
* **`iam/`**: O porteiro do sistema. Divide as permissões entre o que o agente ECS precisa (fazer pull de imagens) e o que a aplicação FastAPI precisa (ler ficheiros Parquet e LSTMs do S3).

---

## Os Ambientes (`environments/`)

Enquanto os módulos são "o que criar", os ambientes definem "como e quanto criar", alimentando os módulos com ficheiros `.tfvars`.

### `dev/` (Desenvolvimento)
Focado na agilidade e redução de custos.
- **Características:** Menos recursos alocados (0.25 vCPU, 512MB RAM), limites menores no Auto Scaling (máx 2 instâncias), retenção mais curta no S3, imagens Docker sobregraváveis (Tags Mutáveis) e permissão de exclusão (`force_destroy = true`).

### `prod/` (Produção)
Focado na estabilidade, segurança e alta disponibilidade.
- **Características:** Maior capacidade base (1 vCPU, 2GB RAM), Auto Scaling agressivo para picos (até 10 instâncias), retenção prolongada de dados, tags Docker Imutáveis (exigindo versionamento semântico limpo) e bloqueio contra exclusão acidental de buckets (`force_destroy = false`).

---

## Gestão de Estado (Backend)

Os ambientes usam **State Remoto e Locking** para permitir que múltiplos engenheiros (ou pipelines CI/CD) façam deploy de forma segura.

O ficheiro `backend.tf` em cada ambiente assegura que:
1. O ficheiro `terraform.tfstate` é guardado num Bucket S3 dedicado e encriptado.
2. É usada uma tabela **DynamoDB** para bloquear (`lock`) a execução. Se duas instâncias de GitHub Actions tentarem fazer deploy simultâneo, uma delas aguardará para evitar corrupção da infraestrutura.

---

## Como fazer o Deploy

1. Certifique-se de que o bucket de estado e a tabela do DynamoDB já existem na sua conta AWS.
2. Navegue até ao ambiente desejado:
   ```bash
   cd deploy/terraform/environments/dev
   ```
3. Inicialize o backend e baixe os módulos:
   ```bash
   terraform init
   ```
4. Reveja as alterações propostas:
   ```bash
   terraform plan
   ```
5. Aplique a infraestrutura (requer confirmação `yes`):
   ```bash
   terraform apply
   ```

No final do `apply`, os `outputs` vão exibir a **URL pública do Load Balancer** para acessar à API e a **URL do repositório ECR** para atualizar nos seus scripts do GitHub Actions.
