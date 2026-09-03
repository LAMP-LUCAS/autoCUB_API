# 🚀 Release v1.0.0 — AutoCUB API: O Primeiro Ecossistema Aberto de Custos da Construção Civil Brasileira (CBIC & NBR 12.721)

> *"A engenharia e a construção civil brasileira dão hoje mais um passo decisivo rumo à modernização, transparência e democratização de dados abertos. Apresentamos o **AutoCUB API v1.0.0**, a solução irmã e complementar do ecossistema [AutoSINAPI](https://github.com/LAMP-LUCAS/autoSINAPI_API), desenvolvida para transformar dados estáticos em inteligência viva, estruturada e consumível programaticamente em escala."*

---

## 🌟 O Que é o AutoCUB API?

Historicamente, o acompanhamento do **Custo Unitário Básico (CUB/m²)** no Brasil sempre dependeu de processos manuais: acessar portais regionais, baixar dezenas de arquivos PDF dispersos entre os sindicatos estaduais, lidar com layouts heterogêneos e digitar valores em planilhas suscetíveis a erros humanos.

O **AutoCUB** nasce para eliminar essa barreira. Projetado como uma API RESTful de alta performance e um pipeline de ETL progressivo e ético, o sistema captura, audita, valida e estrutura os custos da construção civil com rigor absoluto às diretrizes da **ABNT NBR 12.721:2006** e da **Lei Federal nº 4.591/1964**.

O resultado é uma infraestrutura moderna, pronta para auto-hospedagem (*self-hosted*), que abastece plataformas de orçamentação, ERPs da construção civil, incorporadoras imobiliárias e ferramentas como o [Mundo AEC](https://mundoaec.com).

---

## 💎 Destaques Desta Primeira Versão (v1.0.0)

### 1. 📐 Cobertura Completa dos 19 Projetos da NBR 12.721:2006
Todos os 19 projetos-padrão normatizados estão mapeados e enriquecidos com metadados arquitetônicos canônicos:
- **Residenciais**: Padrão Baixo (`R1-B`, `PP-4-B`, `R8-B`, `PIS`), Normal (`R1-N`, `PP-4-N`, `R8-N`, `R16-N`) e Alto (`R1-A`, `R8-A`, `R16-A`).
- **Comerciais**: Salas e Lojas / Andares Livres (`CAL-8`, `CSL-8`, `CSL-16`) nos padrões Normal e Alto.
- **Especiais**: Residência Popular de 1 quarto (`RP1Q`) e Galpão Industrial (`GI`).
- **Enriquecimento Arquitetônico**: Áreas reais, áreas equivalentes de construção, número de dormitórios, vagas de garagem e elevadores.

### 2. 🇧🇷 CUB Médio Brasil Oficial Ponderado (`GET /v1/cub/br`)
Cálculo automatizado do indicador nacional consolidado da CBIC pela média ponderada das 21 capitais:
$$\text{CUB Médio Brasil} = \frac{\sum (P_i \times X_i)}{\sum P_i}$$
Permite analisar a evolução do custo médio da construção brasileira e a participação efetiva de cada estado no bolo econômico.

### 3. ⚡ Cache Redis Ultrarrápido & Rotas Concisas (*Byte-Saving REST*)
- Decorator inteligente `@cache_response(ttl=86400)` servindo relações intra-API pré-calculadas em **menos de 1 milissegundo** diretamente da memória RAM.
- Rotas curtas desenhadas para economizar bytes e otimizar consumo por aplicações web e mobile:
  - `GET /v1/cub/{uf}/dash` — Painel analítico por categoria (Residencial, Comercial, Especial).
  - `GET /v1/cub/{uf}/deson` — Inteligência tributária e economia real/percentual da CPRB (Com vs Sem Desoneração).
  - `GET /v1/cub/{uf}/hist/{cod}` — Série histórica com inflação setorial acumulada.
  - `GET /v1/cub/rank` — Ranking de estados com desvio percentual da média nacional.
  - `GET /v1/cub/comp` — Comparativo direto entre múltiplos estados (`ufs=GO,MG,PR`).

### 4. 🧩 Arquitetura Ports & Adapters (Hexagonal)
Total desacoplamento entre fontes de dados e a API (`autocub/adapters/`):
- `BaseEtlAdapter`: Interface canônica (Port).
- `CbicMonthlyPdfV1Adapter`: Parser vetorial determinístico imune a ruídos de OCR.
- `CbicCrawlerAdapter`: Coletor web ético com backoff, jitter e cookies de sessão.
- `CbicBookletAdapter`: Ingestão dos conhecimentos perenes e normativos.
- `AdapterRegistry`: Resolução dinâmica de adaptadores em tempo de execução.

### 5. 📚 Base Normativa Perene & Calculadoras (`/v1/kb/...` e `/v1/calc/...`)
- `GET /v1/kb/faq`: Perguntas frequentes e lista oficial dos **8 itens não inclusos no CUB** (Fundações, Elevadores, Lazer, Projetos, Terreno, BDI).
- `GET /v1/kb/insumos`: O lote básico de 29 insumos da NBR 12.721 dividido nas 4 famílias macro.
- `GET /v1/kb/lei`: Fundamentação na Lei 4.591/64 e jurisprudência vinculante do STJ.
- `POST /v1/calc/area`: Calculadora paramétrica leve de Área Equivalente de Construção (Quadro II NBR 12.721).

### 6. 🛡️ Pipeline Ético com Validação Temporal & Descoberta Dinâmica
- **Proteção Temporal**: Bloqueia tentativas de coleta para anos futuros e meses ainda não publicados (respeitando o 5º dia útil do mês subsequente).
- **Descoberta Dinâmica**: Mapeia dinamicamente os Sinduscons ativos por estado, detecta UFs que utilizam portais locais (SP, AP, TO) e evita requisições inválidas.

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Papel |
|---|---|---|
| **Linguagem & Runtime** | Python 3.11 / 3.12 | Core da aplicação e processamento numérico |
| **API Framework** | FastAPI + Pydantic v2 | Endpoints assíncronos de alta performance e validação estrita |
| **Banco de Dados** | PostgreSQL 15 | Persistência relacional auditada com chaves compostas |
| **Memória & Cache** | Redis 7 | Cache de sub-milissegundo para respostas intra-API |
| **Processamento Assíncrono** | Celery 5.3 + Flower | Fila de tarefas para ETL progressivo não bloqueante |
| **API Gateway** | Kong Gateway 3.4 | Roteamento, segurança, CORS e rate limiting de borda |
| **Orquestração** | Docker Compose | Subida de todo o ecossistema em um único comando (`make up`) |
| **Testes Automatizados** | Pytest (Unit, Integration, E2E) | 24 testes com 100% de aprovação no pipeline CI/CD |

---

## 🚀 Como Executar em 5 Minutos

```bash
# 1. Clone o repositório
git clone https://github.com/LAMP-LUCAS/autoCUB_API.git
cd autoCUB_API

# 2. Inicialize o ambiente
make setup

# 3. Suba a infraestrutura completa
make up

# 4. Popule os dados iniciais
make populate-db
```

Acesse a documentação Swagger OpenAPI interativa em seu navegador:
👉 **[http://localhost:8002/docs](http://localhost:8002/docs)**

---

## 🤝 O Ecossistema Integrado de Engenharia

O **AutoCUB API** faz parte de uma visão integrada de ferramentas abertas desenvolvidas para apoiar a engenharia civil e a arquitetura no Brasil:
- **[AutoSINAPI](https://github.com/LAMP-LUCAS/autoSINAPI_API)**: Referências de custos e composições públicas (CEF / IBGE).
- **[AutoCUB](https://github.com/LAMP-LUCAS/autoCUB_API)**: Custos unitários da construção civil privada (CBIC / Sinduscons / NBR 12.721).
- **[Mundo AEC](https://mundoaec.com)**: Hub e ecossistema de conteúdo, produtividade e inteligência para profissionais da área.

---

**Licença:** Distribuído sob a licença **GPLv3**.
Desenvolvido com excelência por **Lucas / LAMP Arquitetura** para a comunidade da construção civil brasileira. 🇧🇷🏗️
