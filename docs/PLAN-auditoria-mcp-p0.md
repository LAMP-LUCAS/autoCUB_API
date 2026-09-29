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

## P1/P2 neste repo (adiados)

- §5.4 comparativo descarta UF sem aviso · §5.5 mês de referência inconsistente ·
  §5.3 ranking duplica UF / "média nacional" sobre 9 UFs · §5.6 `cub_latest()` sem
  paginação · §5.7 pavimentos R-8 (**reprocesso** se P2 avançar) · §5.8 aliases.
  → Obs. pós-§5.1: o dedup por UF (uma linha por UF, default do resolver) já
  corrige o **mecanismo** do §5.3 e muda a média para "por estado" — revalidar
  os achados 5.3/5.4/5.5 no P1 contra esse novo comportamento.
  → Obs. nova p/ P1: testes do container gravam no Redis de produção
  (`cub:*` em `autocub-redis`, DB0) — isolar `REDIS_HOST` da suíte (P2).
- **LIM-38** (19/27 UFs — AL AP MS RO RS SE SP TO sem adapter): limitação de
  roadmap, **não é defeito**; não criar teste vermelho por ela.

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
