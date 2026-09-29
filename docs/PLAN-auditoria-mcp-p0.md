# PLAN — Auditoria MCP de Custo (P0) — AutoCUB

> Origem: auditoria externa 2026-09-29 · Plano mestre na casa:
> `SistemaServerLight/docs/plans/PLAN-auditoria-mcp-custo-p0.md`.
> Status: **Em andamento** (2026-09-29).

## Escopo deste repositório (P0)

### §5.2 — `cub_calc_area` 100% inoperante via MCP

**Evidência:** duas formas de payload, mesmo erro nos **dois ramos** da união
(`payload.CalculoAreaRequest.itens → input_type=dict` e
`payload.list[AreaItemInput] → input_type=dict`).
**Hipótese:** contrato FastMCP↔client na união `AreaPayload`
(`autocub_mcp/src/autocub_mcp/tools/tier_2.py` L25-29) — o unit test
`test_calc_area_list_and_cache_partition` passa, o request real falha → mesmo
padrão do bug `env` do OpenCode. **O RED decide o lado** (client × server).

- [ ] **RED:** teste de contrato reproduzindo a chamada real (Fase 0:
      `verify_mcp_audit_claims.py` + teste local com schema serializado).
- [ ] **Fix:** ajustar a tool (param primitivo/discriminated union/Dois tools)
      ou documentar a forma canônica — conforme o diagnóstico.
- [ ] **GREEN:** teste de contrato com payload válido por tool (o auditor
      recomenda: "teste de contrato MCP que exija ao menos um payload válido").

### §5.1 — Divergência de ~20% entre sindicatos da mesma UF (escolha silenciosa)

**Evidência:** `cub_historico`/`cub_deson` → sinduscon 1 (Sinduscon-MG, 2026-06,
3.071,89); `cub_ranking`/`cub_comparativo` → sinduscon 39 (Sinduscon-GV, 2026-08,
2.443,84) — sem aviso.

- [ ] **RED:** teste: UF multi-sindicato (MG/PR) sem `sinduscon_id` explícito →
      hoje escolhe default silenciosamente.
- [ ] **Fix:** (a) `sinduscon_id` obrigatório quando UF tem N>1 sindicato, com
      erro listando candidatos; (b) `sinduscon_id`+`sinduscon_nome` em **todos**
      os endpoints; (c) default documentado e único (mesmo em todos).
- [ ] **GREEN + contrato:** resposta sempre nomeia quem respondeu (id, nome, mês).

## P1/P2 neste repo (adiados)

- §5.4 comparativo descarta UF sem aviso · §5.5 mês de referência inconsistente ·
  §5.3 ranking duplica UF / "média nacional" sobre 9 UFs · §5.6 `cub_latest()` sem
  paginação · §5.7 pavimentos R-8 (**reprocesso** se P2 avançar) · §5.8 aliases.
- **LIM-38** (19/27 UFs — AL AP MS RO RS SE SP TO sem adapter): limitação de
  roadmap, **não é defeito**; não criar teste vermelho por ela.

## Também registrado

- **Positivos a preservar:** `cub_padroes_list` (fiel à NBR 12.721); erros CUB em
  PT-BR com `correlation_id` (bom padrão); `historico == deson` reconciliam.
- Commits local não pushado (`686b9c1`) é trabalho pré-existente — preservado;
  push conjunto apenas depois (decisão 2026-09-29).

## Regras

- TDD (RED antes do fix) · contrato público das tools estável (adições, não remoções) ·
  sem credencial em log/argv/pytest · backup antes de qualquer reprocesso.
