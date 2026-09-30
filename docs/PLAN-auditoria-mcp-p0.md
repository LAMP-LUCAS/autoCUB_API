# PLAN — Auditoria MCP de Custo (P0) — AutoCUB

> Origem: auditoria externa 2026-09-29 · Plano mestre na casa:
> `SistemaServerLight/docs/plans/PLAN-auditoria-mcp-custo-p0.md`.
> Status: **P0 concluído** (2026-09-29) — gate da casa `--p0` 7/7 OK.

## Escopo deste repositório (P0)

### §5.2 — `cub_calc_area` 100% inoperante via MCP

**Evidência:** duas formas de payload, mesmo erro nos **dois ramos** da união
(`payload.CalculoAreaRequest.itens → input_type=dict` e
`payload.list[AreaItemInput] → input_type=dict`).
**Hipótese:** contrato FastMCP↔client na união `AreaPayload`
(`autocub_mcp/src/autocub_mcp/tools/tier_2.py` L25-29) — o unit test
`test_calc_area_list_and_cache_partition` passa, o request real falha → mesmo
padrão do bug `env` do OpenCode. **O RED decide o lado** (client × server).

- [x] **RED:** Fase 0 (`verify_mcp_audit_claims.py`, claim §5.2) — **REFUTOU**:
      o defeito é do **cliente da auditoria** (payload montado fora do contrato),
      não da tool; o server responde nos dois ramos da união.
- [x] **Fix:** NENHUM no server (decisão 2026-09-29: guarda/contrato mantidos
      como estão — nenhum código precisa mudar).
- [x] **GREEN:** gate `--p0` §5.2 OK — "A objeto: custo=102641.28;
      B lista: custo=None (sem codigo_padrao/uf — informativo)".

### §5.1 — Divergência de ~20% entre sindicatos da mesma UF (escolha silenciosa)

**Evidência:** `cub_historico`/`cub_deson` → sinduscon 1 (Sinduscon-MG, 2026-06,
3.071,89); `cub_ranking`/`cub_comparativo` → sinduscon 39 (Sinduscon-GV, 2026-08,
2.443,84) — sem aviso.

- [x] **RED:** `tests/integration/test_sindicato_deterministico.py` (4 testes,
      rodaram no container): reproduziram exatamente a evidência —
      `historico(id=1) × ranking MG(id=None)`, MG/PR duplicados no ranking,
      default de `calc/area` no sinduscon parado.
- [x] **Fix:** (b)+(c) implementados juntos — **default único e determinístico**
      em `autocub/api/resolvers.py` (`resolver_sinduscon`: sinduscon **ativo**
      da UF com o **dado mais recente**, empate → menor id; `sinduscon_id`
      explícito continua honrado onde existe) aplicado em brasil, panorama,
      desoneração, histórico, `calc/area` e na escolha por UF de
      ranking/comparativo; **`sinduscon_id` + `sinduscon_nome`** em `RankingItem`,
      `ComparativoItem` e `CubBrasilItem` (adições, sem remoção de contrato);
      `sinduscon_id` que era **aceito e ignorado** em `impacto-desoneracao`
      agora é honrado. Ranking/comparativo passam a ter **uma linha por UF**.
- [x] **GREEN + contrato:** 31 testes passando (4 novos + suíte existente);
      gate `--p0` §5.1 OK — `historico(id=39, Sinduscon-GV) × ranking MG(id=39,
      Sinduscon-GV, valor=2443.84)`; resposta nomeia id, nome e mês
      (`data_referencia` no envelope).

## P1 concluído neste repo (2026-09-30)

- [x] **§5.3 ranking amostra declarada** — RED
      `tests/integration/test_p1_ranking_comparativo.py` → fix: `RankingResponse`
      ganha `ufs_incluidas` + `cobertura_pct` (a "média nacional" é uma amostra;
      declarar quem compõe). GREEN ao vivo: `total=9 distintas=9 duplicatas=0;
      média qualificada=True` (o dedup do §5.1 já tinha zerado as duplicatas).
- [x] **§5.4 comparativo sinaliza UF ausente** — mesmo arquivo RED → fix:
      `ComparativoResponse.ufs_nao_encontrados` lista UFs pedidas sem dado
      (SP sem adapter). GREEN ao vivo: menções a SP: True.
- [ ] §5.5 mês de referência — **já GREEN via §5.1** (mesmo default
      determinístico em histórico e comparativo; gate OK).

## Fase 5 (P2) concluída neste repo (2026-09-30)

- [x] **§5.6 `cub_latest` paginado** — `limit` default 50, `0` = ilimitado
      (decisão do usuário); RED `tests/test_latest_pagination.py` → fix no
      endpoint/`response_model`; gate: `default=50 | limit=7=7 | limit=0=418`
      (`9a9923c`).
- [x] **Redis da suíte isolado** — testes do container não gravam mais em
      `cub:*` do Redis de produção (`0126404`, obs. do P1).
- [x] **§5.8 stage + fonte + aliases** — `stage` no health (produção
      declarada `production` via `.env`), `fonte` por UF no panorama, aliases
      `cub_dash`/`cub_impacto_desoneracao` deprecados (`6e99c0b` + seed Kong
      `d5aa4ef`/`5b7ef7a` na casa); gate 22/22.
- [x] **§2.2 guard** — nenhuma tool com descrição vazia (`9478c4b`).
- [x] **§2.1 MCP resources** — RED (`resources: []`) → `resources.py` com
      `autocub://guia/endpoints` + `autocub://referencia/padroes-nbr`
      (`78e29bc`); suíte MCP 67→73; gate 28/28.
- [x] **LIM-38 — nota no response** (decisão 2026-09-30, **sem RED** — o
      claim cobre *sinalização*, nunca a cobertura): `autocub/api/lim38.py`
      (`BR_UFS` + `NOTA_LIM38`), `/latest?uf=<sem adapter>` → envelope
      `{uf, items: [], nota_lim38}` (UF coberta segue lista plana), nota nos
      4 404 de cobertura (guarda: código inválido ≠ cobertura), MCP repassa
      `detail` do 404 e `cub_get_uf` converte marcador `LIM-38` em resposta
      (`4b255fe`); gate 30/30.
- [x] **§5.7 pavimentos R-8 — documentado e adiado** (investigação do
      usuário; reprocesso exige backup): nota "⚠️ Pendência conhecida" em
      `docs/GUIA_ENDPOINTS_E_REGRAS_DE_NEGOCIO.md` §4 (`beb2702`); sem gate
      claim, por decisão.

## Também registrado

- **Positivos a preservar:** `cub_padroes_list` (fiel à NBR 12.721); erros CUB em
  PT-BR com `correlation_id` (bom padrão); `historico == deson` reconciliam.
- Commits local não pushado (`686b9c1`) é trabalho pré-existente — preservado;
  push conjunto apenas depois (decisão 2026-09-29).
- **Cache pós-deploy:** flush obrigatório de `cub:*` (`autocub-redis`) +
  `respcache:*` (Kong `api-gateway-redis`) — payload antigo de `cub:*` sem
  `sinduscon_id` daria 500 de validação no response_model novo.

## Regras

- TDD (RED antes do fix) · contrato público das tools estável (adições, não remoções) ·
  sem credencial em log/argv/pytest · backup antes de qualquer reprocesso.

---

## STORY-MCP-007 — Certificação funcional (2026-09-30) · CONCLUÍDA

Ondas 1–4 implementadas com TDD (RED comportamental no gate da casa → fix →
GREEN). Veredito por item (medido ao vivo antes de cada fix) em
`docs/projects/STORY-MCP-007-certificacao-funcional-mcp-custo.md` (casa).

| Onda | Itens | Entrega |
|---|---|---|
| 1 | S-01, S-03, S-04, S-05 | fail-loud: erro nomeado, curva ABC sem código órfão, auditoria nomeia a última data, rótulo por tipo |
| 2 | S-02, C-01, C-04 | preço ausente = `null`+motivo; envelope de vazio no MCP; calc_area rejeita lista e explica a falta de CUB |
| 3 | X-01 | número é JSON number (Decimal no cálculo, float na resposta — ADR 009) |
| 4 | C-02, C-03 | `cub_health.cobertura`; guarda de sanidade na ingestão; diagnóstico AM/AC/PI documentado |

Itens **fora de escopo de código** (documentados, não corrigidos aqui):
- C-02 dados: 6 UFs sem cadastro (AL, AP, MS, RS, SP, TO) + RO/SE sem cotação
  — exige decisão de fonte (Sinduscon-SP) e adapter.
- C-03 causa do rebase de AM: diagnóstico em
  `docs/DIAGNOSTICO_DADOS_AM_AC_PI.md`; **nenhum dado foi reprocessado**
  (exige backup + autorização).
- S-06: não reproduzido a quente (0,23–0,28 s); medir com cache frio antes.
- C-05: visão global já existe via `cub_latest(limit=0)` (§5.6); falta
  `total`/`has_more` e doc da ordenação.

**Gate:** 39/39 (exit=0). Suítes: SINAPI API 354 · SINAPI MCP 144+ ·
AutoCUB API 60 · AutoCUB MCP 82 · AutoINCC 122.
