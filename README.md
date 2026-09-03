# 🏗️ autoCUB API: A sua ponte para os dados do CUB/m²

[![Versão](https://img.shields.io/badge/version-v0.1.0-orange.svg)](https://github.com/LAMP-LUCAS/autoCUB_API)
[![Licença](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![Powered by: FastAPI](https://img.shields.io/badge/Powered%20by-FastAPI-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Norma](https://img.shields.io/badge/ABNT-NBR%2012.721:2006-yellow.svg)](https://cbic.org.br)

**Chega de perder tempo baixando PDFs de Sinduscons todo mês.** A **autoCUB API** é uma solução *open-source* projetada para automatizar a coleta, extração e disponibilização estruturada dos dados do **Custo Unitário Básico da Construção Civil (CUB/m²)** no Brasil, publicados mensalmente pelo portal `cub.org.br` da CBIC.

Esta solução foi concebida como **projeto irmão do [autoSINAPI](https://github.com/LAMP-LUCAS/AutoSINAPI)** e integra o ecossistema de dados abertos para a construção civil (**Mundo AEC**), permitindo análises de viabilidade, orçamentação paramétrica, benchmarking regional e integração com ERPs e dashboards de BI.

---

### 💡 O Fim da Coleta Manual do CUB

| ❌ **O Jeito Antigo (e Doloroso)** | ✅ **A Solução autoCUB API** |
| ------------------------------------ | ----------------------------------- |
| Baixar PDFs avulsos de cada Sinduscon todo mês. | Pipeline de ETL progressivo e automatizado. |
| Dados presos em tabelas PDF difíceis de raspar. | Respostas padronizadas em JSON via API RESTful. |
| Dificuldade para montar séries históricas regionais. | Histórico completo de 2007 até o presente mês. |
| Confusão com variações de padrões da NBR 12.721. | 19 projetos-padrão normalizados e validados. |
| Desconsideração da desoneração da folha. | Séries com e sem desoneração de mão de obra. |

---

### 🌐 Integração com o Ecossistema Mundo AEC

O **autoCUB** compartilha a mesma arquitetura de dados e infraestrutura de microsserviços do **[autoSINAPI_API](https://github.com/LAMP-LUCAS/autoSINAPI_API)** e do futuro **autoINCC**:

```
                       ┌─────────────────────────────────────┐
                       │           Kong API Gateway          │
                       │    (ou Gateway Unificado AEC)       │
                       └──────────────────┬──────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
     ┌────────────────────────┐                      ┌────────────────────────┐
     │     autoSINAPI_API     │                      │      autoCUB_API       │
     │  (Insumos & Composições│                      │    (CUB/m² Regional    │
     │   Caixa Econômica)     │                      │   19 Projetos NBR)     │
     └────────────┬───────────┘                      └────────────┬───────────┘
                  │                                               │
       ┌──────────┴──────────┐                         ┌──────────┴──────────┐
       │ Celery ETL Worker   │                         │ Celery ETL Worker   │
       │ (Download Caixa ZIP)│                         │ (Coleta CUB.org.br) │
       └─────────────────────┘                         └─────────────────────┘
```

---

### ⚡ Comece a Usar em 5 Minutos (Auto-Hospedado)

Suba toda a infraestrutura com Docker Compose utilizando o `Makefile`:

#### 1. Configurar o Ambiente
```bash
make setup
```
*(Cria o arquivo `.env` a partir de `.env.example`)*

#### 2. Subir a Infraestrutura
```bash
make up
```
*(Inicia os containers `cub_db` [PostgreSQL], `cub_redis`, `cub_api` [FastAPI] e `cub_celery_worker`)*

#### 3. Popular o Banco de Dados
```bash
make populate-db
```
*(Executa o ETL progressivo baixando e extraindo os dados do CUB/m²)*

#### 4. Acessar a Documentação Interativa
Acesse a documentação Swagger OpenAPI em seu navegador:
👉 **[http://localhost:8002/docs](http://localhost:8002/docs)**

### 🧩 Arquitetura de Adapters (Ports & Adapters / Hexagonal)

Para garantir que modificações futuras nos layouts dos relatórios mensais da CBIC ou inclusão de novas fontes não quebrem a API, o processamento segue o padrão desacoplado de adaptadores (`autocub/adapters/`):

- **`BaseEtlAdapter`**: Interface abstrata (Port) definindo métodos padronizados `can_handle()`, `extract()` e `transform()`.
- **`CbicMonthlyPdfV1Adapter`**: Adaptador especializado na leitura e extração vetorial determinística dos relatórios mensais em PDF (NBR 12.721:2006).
- **`CbicCrawlerAdapter`**: Adaptador de coleta web responsável por gerenciar sessões HTTP, CSRF, cookies e taxa de requisições com jitter.
- **`CbicBookletAdapter`**: Adaptador para ingestão e estruturação dos dados perenes das Cartilhas Oficiais e da Lei Federal 4.591/64.
- **`AdapterRegistry`**: Registro dinâmico de adaptadores com fábrica de resolução em tempo de execução.

👉 **Documentação Completa do Consórcio CBIC e Adapters Futuros (SP, RS, AP, TO):** [`docs/CONSORCIO_CBIC_E_ADAPTERS.md`](docs/CONSORCIO_CBIC_E_ADAPTERS.md)

---


### 📁 Usando PDFs Locais do CUB (Cache / Offline)


Para evitar sobrecarregar os servidores da CBIC e acelerar a carga de dados históricos, o autoCUB adota o mesmo princípio do autoSINAPI: **cache local em disco**.

1. Os relatórios baixados são salvos automaticamente em:
   ```
   autocub_downloads/{UF}/{sinduscon_id}/cub_{ANO}_{MES}_{desoneracao}.pdf
   ```
2. Se você já possuir arquivos baixados, basta posicioná-los na pasta correspondente. O coletor detectará os arquivos e pulará as requisições web, garantindo execução ultrarrápida e 100% ética.

---

### 📐 Os 19 Projetos-Padrão da NBR 12.721:2006

O autoCUB estrutura rigorosamente os 19 projetos da norma:

| Categoria | Padrão | Códigos Canônicos | Descrição |
|---|---|---|---|
| **Residencial** | Baixo | `R1-B`, `PP-4-B`, `R8-B`, `PIS` | Casa unifamiliar térrea, prédio popular (4 pav.), prédio (8 pav.) e habitação social. |
| **Residencial** | Normal | `R1-N`, `PP-4-N`, `R8-N`, `R16-N` | Casa unifamiliar térrea, prédio (4, 8 e 16 pavimentos). |
| **Residencial** | Alto | `R1-A`, `R8-A`, `R16-A` | Casa unifamiliar térrea, prédios de 8 e 16 pavimentos de alto padrão. |
| **Comercial** | Normal | `CAL-8-N`, `CSL-8-N`, `CSL-16-N` | Salas e lojas ou andares livres (8 e 16 pavimentos). |
| **Comercial** | Alto | `CAL-8-A`, `CSL-8-A`, `CSL-16-A` | Salas e lojas ou andares livres de alto padrão. |
| **Especial** | Único | `RP1Q`, `GI` | Residência Popular de 1 quarto e Galpão Industrial. |

---

### 🔌 Principais Endpoints da API (Byte-Saving REST & Redis Cache)

| Método | Rota Concisa | Rota Legada / Alias | Descrição |
|---|---|---|---|
| `GET` | `/v1/cub/br` | - | **CUB Médio Brasil Oficial**: Média ponderada das 21 capitais (Quadro I e II CBIC) |
| `GET` | `/v1/cub/latest` | - | Cotações mais recentes com **origem completa** (UF, Sinduscon, Região) |
| `GET` | `/v1/cub/{uf}` | - | Cotações de todos os padrões para o estado e período especificado |
| `GET` | `/v1/cub/{uf}/dash` | `/v1/cub/{uf}/panorama` | **Dashboard Analítico**: Estrutura NBR, médias e destaques (Cache Redis) |
| `GET` | `/v1/cub/{uf}/deson` | `/v1/cub/{uf}/impacto-desoneracao` | **Inteligência Tributária**: Economia R$/m² da desoneração da folha (Cache Redis) |
| `GET` | `/v1/cub/{uf}/hist/{cod}` | `/v1/cub/{uf}/historico/{cod}` | **Série Histórica**: Inflação setorial acumulada e médias mensais (Cache Redis) |
| `GET` | `/v1/cub/rank` | `/v1/cub/ranking` | **Ranking Nacional**: Posição e desvio percentual da média (Cache Redis) |
| `GET` | `/v1/cub/comp` | `/v1/cub/comparativo` | Comparativo de custos entre múltiplos estados (ex: `ufs=GO,MG,PR`) |
| `GET` | `/v1/kb/faq` | - | **Base Perene**: Perguntas frequentes e itens oficiais **não inclusos** no CUB |
| `GET` | `/v1/kb/insumos` | - | **Base Perene**: Lote básico dos 29 insumos e 4 famílias macro da NBR 12.721 |
| `GET` | `/v1/kb/lei` | - | **Base Perene**: Fundamentos da Lei Federal 4.591/1964 e jurisprudência STJ |
| `GET` | `/v1/kb/nbr` | - | **Base Perene**: Fatores de equivalência de custo normatizados (Quadro II) |
| `POST`| `/v1/calc/area` | - | **Calculadora**: Área Equivalente de Construção (Quadro II NBR 12.721) |
| `GET` | `/v1/padroes` | - | Catálogo dos 19 projetos-padrão enriquecidos com áreas e dormitórios |
| `GET` | `/v1/sinduscons` | - | Lista os Sinduscons e UFs ativas na base |
| `POST`| `/v1/admin/etl/trigger` | - | Disparo assíncrono do pipeline ETL via Celery |
| `GET` | `/v1/admin/etl/logs` | - | Logs de telemetria e auditoria das execuções |



---

### 🧪 Testes Automatizados

O projeto possui suíte de testes com validação contra PDFs reais de produção:

```bash
pytest -v
```

---

### 📄 Licença

Distribuído sob a licença **GPLv3**. Veja `LICENSE` para mais informações.
