# Manual de manutenção — autoCUB_API

> Para quem vai **mudar** este repo. O que fazer, o que não fazer, e por quê.
> Complementa o [GUIA_DE_REGRAS_DE_NEGOCIO](GUIA_ENDPOINTS_E_REGRAS_DE_NEGOCIO.md)
> (o contrato de cada endpoint) — este documento é o **como manter**.

---

## 1. A doutrina que governa este repo

Uma regra rege quase todas as decisões, e ela nasceu de um erro nosso:

> **Só há sinal com FATO medido. Na dúvida, não alerte — verifique.**

### 1.1 A história que explica a regra (leia antes de "melhorar" qualquer coisa)

Em 2026-09-30 a série do **AM** repetia valor (maio = junho = abril). Montamos um
detector que marcava essas cotações como `provisorio: true`, com o alerta
"república/forward-fill — confirme o boletim antes de orçar", na resposta das
tools.

Em 2026-10-01 baixamos os PDFs **direto do `cub.org.br`** (não do nosso cache):

```
2026-05   fonte sha=5aaf71eb   R1-N = 3897,23
2026-06   fonte sha=fac773eb   R1-N = 3897,23     ← a FONTE mantém o índice
```

19/19 itens idênticos com a base. **O Sinduscon-AM publica o mesmo índice em
maio e junho.** Nossa carga estava fiel; a hipótese de erro nosso era falsa; e o
alarme passou a injetar desconfiança em número oficial — com o **risco inverso**
ao do defeito que ele corrigia (o agente podia recusar valor válido).

**O que ficou como mecanismo:** a verificação de verdade (seção 4). O alarme foi
removido. `git log` tem o antes e o depois.

### 1.2 As três regras derivadas

| Regra | Na prática |
|---|---|
| **Nunca desacreditar o valor oficial** | Repetição de valor entre competências é fato da fonte. Nenhuma resposta de tool diz que o dado é suspeito. |
| **Ausência de dado ≠ erro** | `isError=false` + envelope com `status`, `disponivel`, `motivo`, `alternativas`, `orientacao`. `content` **nunca** vazio. |
| **Erro tem código, causa e `correlation_id`** | `INVALID_UF: …`, `AUDIT_NOT_FOUND: … a última competência é 2021-12`. |

### 1.3 Jargão interno nunca vaza ao cliente

Identificadores de ticket (`LIM-38`) e vocabulário de engenharia (`adapter`,
`ETL`, `roadmap`) ficam no **log do servidor**. O corpo fala linguagem de
domínio. Isso é asserido por claim (§5) — se você adicionar um desses termos na
resposta, o gate fica vermelho.

---

## 2. Mapa do código (onde cada coisa mora)

```
autocub/
├── api/                    ← camada HTTP (FastAPI)
│   ├── main.py             health + cobertura + conferência da fonte
│   ├── lim38.py            texto canônico da nota de cobertura (fonte)
│   ├── roadmap.py          por que cada UF está sem dado (fato do banco)
│   └── routers/
│       ├── cub.py          cotações, dash, comparativo, ranking, histórico…
│       └── calc.py         calculadora NBR 12.721 (/calc/area)
├── processor/              ← domínio de dados (o coração)
│   ├── schemas.py          schemas de resposta (Num = Decimal→float)
│   ├── parser.py           extrai itens do PDF
│   ├── sanity.py           guarda de variação implausível (quarentena)
│   ├── conferencia.py       ★ verificação da fonte (C1 período, C2 gravação)
│   └── repeticao.py        detecta índice mantido entre competências (fato)
├── adapters/               coleta: CBIC (crawler, monthly_pdf, booklet)
├── downloader/             http/sessão/cache de PDFs
├── tasks/etl_tasks.py      pipeline: conferir → gravar → conferir
└── database/               modelos, loader (upsert), seed

autocub_mcp/                ← servidor MCP (o que o AGENTE consome)
├── envelope.py             ★ contrato único (status/disponivel/motivo/…)
├── tools/tier_1.py         choke point `_get` (11 tools passam por ele)
├── tools/tier_2.py         cub_calc_area
└── resources.py            documentação que o agente lê (resource)
```

**As três estrelas (`envelope.py`, `conferencia.py`, `sanity.py`) são o coração.**
Tudo o que é resposta de agente nasce em `envelope.py`; todo o que protege a
ingestão nasce em `conferencia.py`/`sanity.py`.

---

## 3. O contrato de resposta (invariantes)

Toda tool do MCP responde **o mesmo envelope**, nos dois caminhos:

```jsonc
// com dado
{ "status": "ok", "disponivel": true, "consulta": {...},
  "vigencia": {...}, "items": [...], "total": 19, /* campos próprios da tool */ }

// sem dado
{ "status": "sem_dado", "disponivel": false, "consulta": {...},
  "motivo": { "codigo": "CUB_NAO_PUBLICADO_POR_UF", "descricao": "...", "natureza": "limitacao_externa" },
  "vigencia": {...}, "alternativas": {...}, "orientacao": {...},
  "itens": [], "total": 0 }
```

Invariantes que **não podem quebrar** (todas com claim no gate):

1. `status ∈ {ok, sem_dado}`; `disponivel` coerente com `status`.
2. `disponivel: false` **nunca** vem com `valor_m2`.
3. `motivo` é **objeto** com `codigo` do catálogo + `natureza`; nunca texto livre.
4. `natureza` ∈ `limitacao_externa` · `ingestao_pendente` · `defasagem` · `parametro_invalido`.
5. `content` com **≥1 bloco**, sempre.
6. Erros trazem `correlation_id`.
7. Sem jargão interno no corpo.

> **Histórico de contrato:** antes da Onda A (2026-09-30) o envelope só existia
> no caminho "sem dado" e havia 4 formatos diferentes entre as 13 tools (5
> devolviam texto puro com `isError=true`). Hoje é um só, nos dois caminhos.

---

## 4. A pipeline de ingestão (e onde cada guarda age)

`process_single_cub_report` (`tasks/etl_tasks.py`) — a ordem importa:

```
1. baixa/usa o PDF do cache
2. parseia (processor/parser.py)
3. ★ C1  conferência do PERÍODO (processor/conferencia.py)
        confere      → segue
        divergente   → NÃO GRAVA. status=CONFERIU_DIVERGENTE (fato: o arquivo
                       declara outra competência)
        indeterminado→ segue, e registra "não conferível" (nunca bloqueia)
4. monta os records
5. índice mantido (processor/repeticao.py) → FATO, informativo
6. guarda de sanidade (processor/sanity.py) → |var| > 5% vai para quarentena
7. upsert (database/loader.py)   ← on_conflict_do_update: SOBRESCREVE
8. ★ C2  releitura do banco e conferência gravação × PDF
        divergência → status=CONFERIU_DIVERGENTE + log ERROR
9. grava: etl_execucoes (status + mensagem, sem DDL) + JSON em data/conferencia/
```

### Por que a C1 lê o rótulo do PDF (e não confia no nome do arquivo)

O PDF carrega a competência no texto. **Dois formatos reais** (medidos em 1.144
arquivos):

```
(NBR 12.721:2006 - CUB 2006) - Junho/2026                      ← AM, RJ, GO…
CUB/m² dados de Dezembro/2025, para ser usado em Janeiro/2026   ← RR…
```

No segundo, a competência é a de **USO**, não a de "dados de". Ler a errada
marcaria divergência em 100% dos arquivos daquele formato — por isso
`conferencia.py` tem dois padrões, com o de uso em preferência.

Resultado da medição (2026-10-01): **1.117 confere · 22 divergentes · 5
indeterminados**. Os 22 divergentes eram **cache órfão** (PDF de 2016/2019/2023
com nome de arquivo 2026) — cruzados com o banco, **nunca foram ingeridos**.

### Por que a C2 existe

Nenhum outro check enxerga erro de **chave**: valor gravado na UF/competência/
desoneração errada. A C2 relê do banco só o que foi gravado e compara com o
PDF. Custa um `SELECT` por lote.

### Regra de ouro da quarentena

**Descarte é pior que sinalizar.** A guarda de sanidade não apaga nada — joga
para quarentena e registra. Um buraco calado na série é pior que um valor
suspeito **assinalado**.

---

## 5. Como manter (receitas)

### 5.1 Adicionar uma tool nova
1. Escreva a função em `tools/tier_1.py` (ou `tier_2.py`).
2. Passe por `_get(path, params, ctx, consulta={...})` — **o envelope sai
   automático** (inclusive `vigencia`). Não monte o dict à mão.
3. Registre em `server.py` (`TOOLS`) com descrição que **diga ao agente o que
   precisa saber** (formato, limites, o que significa "sem dado").
4. Escreva teste em `autocub_mcp/tests/` (mock do client, padrão `_patch`).
5. Se é nova consulta, considere `consulta=` para o envelope echoar o pedido.

### 5.2 Adicionar uma guarda de ingestão
1. Novo concern em `processor/` (funções puras, testáveis sem banco).
2. **Tri-estado** sempre que puder dar "não sei": `confere` / `divergente` /
   `indeterminado`. Nunca binário.
3. Testes em `tests/unit/` com **exemplos reais** (copie uma linha de PDF
   real para o teste).
4. Ligue na `etl_tasks.py` na ordem correta e registre o resultado em
   `etl_execucoes` (status ≤ **20 caracteres**, é `varchar(20)`).
5. **Não** coloque o veredito na resposta da tool (regra 1.2). Fato no log e no
   health; valor na tool, limpo.

### 5.3 Mudar o contrato de resposta
- `envelope.py` é o único lugar. `claims` do gate (seção 6) avisam se quebrar.
- Coerência > formato: se um campo é padrão, é padrão nas 13 tools.

### 5.4 Rodar a verificação (gate)
O gate vive na **casa** (`automation/scripts/verify_mcp_audit_claims.py`), não
neste repo — ele fala com os 3 MCPs ao vivo pelos gateways públicos.

```bash
# 1. flush das 3 camadas + Kong (obrigatório antes do gate)
for r in autosinapi_redis autocub_redis autoincc_redis; do
  docker exec $r redis-cli -n 0 FLUSHDB
done
REDIS_CONTAINER=api-gateway-redis bash stacks/autosinapi/kong/scripts/flush_cache.sh

# 2. rodar
python3 automation/scripts/verify_mcp_audit_claims.py    # exit 0 = tudo verde
```

Cada claim = 1 asserção de comportamento **contra o gateway real**. É o
"teste de aceitação" do produto. Ao mexer em resposta/ingestão, rode o gate.

### 5.5 Testes deste repo
```bash
# API (dentro do container: tem Postgres/Redis de teste)
docker exec autocub_api python -m pytest tests/ -q

# MCP (local, sem infra)
cd autocub_mcp && PYTHONPATH=src python3 -m pytest tests/ -q
```

> ⚠️ **`tests/` é baked na imagem; `autocub/` é bind-mount.** Mudou teste? Faz
> `docker compose build api && up -d api` — senão o container roda o teste velho.
> (É por isso que CI faz build antes de testar.)

---

## 6. Diagrama das claims do gate (mapa do comportamento travado)

| Claim | O que trava |
|---|---|
| `C-10` | contrato único de "sem dado" (status/disponivel/motivo) |
| `C-11` | vigência em resposta com dado (vigente + meses_de_atraso) |
| `P1-1` | sem jargão interno no corpo; `calc_area.motivo` é objeto |
| `P1-2` | envelope padrão **também** no caminho com dado |
| `B-01` | índice mantido declarado como **fato**, sem desacreditar o valor |
| `B-01x` | conferência da fonte observável; divergência só com fato |
| `B-02` | comparativo com data por item; período pedido × servido |
| `B-04` | `cub_latest` navegável (`meta_navegacao`) |
| `X-01` | número é JSON `number`, não string (ADR 009) |

---

## 7. Armadilhas conhecidas (não caia de novo)

| Armadilha | O que fazer |
|---|---|
| **`status` é `varchar(20)`** | Status novo precisa caber. `SUCESSO_QUARENTENA` = 18, `+PROV` estoura. |
| **Cache com pastas cruzadas** | `autocub_downloads/AM/16/` tem PDFs de **PE** (id antigo). Não confie na pasta: o id do cache é de outra época. Resolva pela UF. |
| **UF multi-sindicato** | MG tem 3 (id 1, 32, 39) com competências diferentes. `cub_get_uf` ordena por competência desc e marca `recomendado`. |
| **Ciclo de import** | `autocub.adapters` ↔ `autocub.downloader`. Em script avulso, importe `autocub.tasks` **primeiro**. |
| **Pydantic v2 + `Decimal`** | Serializa como **string**. Use o tipo `Num` (`processor/schemas.py`). |
| **Não testar na porta da ingestion** | `upsert_cub_records` sobrescreve (`on_conflict_do_update`) e não guarda histórico. Confirme a competência **antes**. |
| **Nomes em português no PDF** | `Junho/2026`, `Março/2023` (com acento). O extrator normaliza. |

---

## 8. Reprocessar dados (com segurança)

Reprocessar é escrita destrutiva em produção (o `upsert` sobrescreve e não há
histórico de valores). Checklist — derivado do que fizemos em 2026-10-01:

1. **Backup + verificar.** `pg_dump` do banco; **restaure** num banco de rascunho
   e compare o `md5` do conteúdo (`cub_mensal`) com o de produção. Um dump não
   testado não é backup.
2. **Backup legível.** Exporte as linhas alvo em CSV — rede de segurança que se
   lê sem Postgres.
3. **Dry-run e DIFF, sem gravar.** Parseie o PDF e compare com o banco. É assim
   que descobrimos que o banco de AM estava fiel (19/19) e o "defeito" era da
   fonte. Diff primeiro, decisão depois.
4. **Aprovar a gravação** explicitamente (regra do projeto).
5. **Gravar** (upsert) e rodar a verificação depois.

> Backup de 2026-10-01, se precisar: `backups/cub_20261001_0704_pre-reprocess-AM.sql`
> (sha256 `6851bc81…`, verificado por restauração).

---

## 9. Leitura do health (diagnóstico)

`GET /v1/health` → `cobertura`:

| Bloco | O que diz |
|---|---|
| `ufs_com_dado` / `ufs_sem_dado` | quem tem e quem não tem CUB (fato do banco) |
| `detalhe_ufs_sem_dado` | por que a UF está sem dado + `previsto_para` |
| `series_indice_estavel` | séries que **mantiveram** o índice entre competências (fato da fonte) |
| `conferencia_da_fonte` | última conferência por UF; `divergencias` **só com FATO** |

Quando `conferencia_da_fonte.divergencias` não vier vazio, há um arquivo de
competência errada no acervo — investigue antes de reprocessar.

---

## 10. Referências

- **Regras de negócio por endpoint:** [GUIA](GUIA_ENDPOINTS_E_REGRAS_DE_NEGOCIO.md)
- **Diagnóstico de dados (AM/AC/PI):** [DIAGNOSTICO_DADOS_AM_AC_PI.md](DIAGNOSTICO_DADOS_AM_AC_PI.md)
- **Consórcio CBIC e adapters futuros:** [CONSORCIO_CBIC_E_ADAPTERS.md](CONSORCIO_CBIC_E_ADAPTERS.md)
- **ADRs (repo irmão autoSINAPI, aplicáveis aqui):**
  - **ADR 009** — tipagem: `Decimal` no cálculo, `float` na resposta JSON.
  - **ADR 010** — fail-loud: erro nomeado, `correlation_id`, ausência de dado
    não é erro.
- **Histórico de correções MCP:** [PLAN-auditoria-mcp-p0.md](PLAN-auditoria-mcp-p0.md)