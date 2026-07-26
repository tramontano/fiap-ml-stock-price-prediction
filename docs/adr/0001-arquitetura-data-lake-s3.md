# ADR-001: Adoção da Arquitetura Medallion com MinIO para Data Lake

**Status:** Aceito
**Data:** 2026-06-06
**Autores:** Tech Challenge - Fase 4 (FIAP)
**Revisores:** Arquitetura de ML Engineering

---

## Contexto

O projeto Stock Price Prediction necessita de uma estratégia robusta de gerenciamento de dados que suporte múltiplas etapas de processamento, desde a ingestão bruta até a preparação final de features para modelos de Machine Learning. A solução deve:

- Manter rastreabilidade completa dos dados através de todas as transformações.
- Permitir auditoria e reprodutibilidade de experimentos.
- Facilitar a detecção e correção de problemas de qualidade de dados.
- Suportar tanto ambientes de desenvolvimento local quanto produção em AWS.
- Escalar eficientemente conforme o volume de dados e número de tickers aumentam.

Adicionalmente, a infraestrutura local de desenvolvimento deve replicar fielmente o comportamento de produção, minimizando discrepâncias entre ambientes.

---

## Decisão

Adotamos a **Arquitetura Medallion** (também conhecida como "Bronze-Silver-Gold") como padrão de organização do Data Lake, combinada com **MinIO** como solução de armazenamento compatível com S3 para desenvolvimento local.

### Arquitetura Medallion

A estrutura de dados é organizada em três camadas progressivas de refinamento:

**Camada Bronze (Raw Data):**

- Armazenamento imutável de dados brutos extraídos diretamente do Yahoo Finance.
- Nenhuma transformação ou limpeza é aplicada.
- Serve como fonte de verdade (single source of truth) para auditoria e rollback.
- Retenção indefinida para análise histórica e compliance.

**Camada Silver (Processed Data):**

- Dados limpos, validados e preparados para feature engineering.
- Transformações aplicadas: remoção de NaN, validação de sequência temporal, seleção de colunas OHLCV.
- Rastreabilidade completa até registros Bronze originais.
- Logs de transformação documentam registros removidos e motivos.

**Camada Gold (Feature Store):**

- Features engineerizadas, normalizadas e prontas para consumo por modelos.
- Transformadores customizados: DailyReturnTransformer, RSITransformer, EMATransformer, FeatureSelector.
- Formato otimizado para treinamento de redes neurais (arrays NumPy em Parquet).
- Versionamento por run_id do MLflow para rastreabilidade de experimentos.

### MinIO para Desenvolvimento Local

MinIO é um servidor de armazenamento de objetos compatível com a API S3 da Amazon, permitindo:

- **Paridade com Produção:** Código desenvolvido localmente com MinIO funciona sem alterações em AWS S3 em produção.
- **Zero Overhead de Infraestrutura:** Executa em Docker Compose sem custos adicionais.
- **Facilidade de Debugging:** Interface web integrada para inspeção de buckets e objetos.
- **Suporte a Transações Distribuídas:** Garante consistência de dados entre camadas.

---

## Consequências

### Positivas

1. **Rastreabilidade Completa:** Cada versão de dados é preservada e auditável, facilitando investigação de anomalias.

2. **Reprodutibilidade:** Experimentos podem ser reexecutados exatamente com os mesmos dados, essencial para validação científica.

3. **Escalabilidade:** A estrutura suporta crescimento natural: novos tickers, novos indicadores técnicos, novos modelos.

4. **Paridade Desenvolvimento-Produção:** MinIO local espelha exatamente o comportamento de AWS S3, reduzindo surpresas em deployment.

5. **Separação de Responsabilidades:** Cada camada tem um propósito claro, facilitando manutenção e debugging.

### Negativas

1. **Overhead de Armazenamento:** Três cópias dos dados (Bronze, Silver, Gold) aumentam consumo de disco. Mitigado por compressão Snappy em Parquet.

2. **Curva de Aprendizado:** Equipes acostumadas com bancos de dados relacionais precisam adaptar-se ao paradigma de data lakes.
