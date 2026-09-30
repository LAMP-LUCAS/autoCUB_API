# Diagnóstico de dados CUB — AM, AC, PI (STORY-MCP-007/C-03)

> Medido em 2026-09-30 contra o banco de produção (`cub`).
> **Nenhum dado foi reprocessado** — este documento é diagnóstico + decisão
> pendente. Reprocessar exige backup e autorização (regra do projeto).

## 1. Resumo

| Achado | Situação | Natureza |
|---|---|---|
| **AM** variação −12,44% a −4,85% em 2026-07 | série provavelmente **corrompida** (ou rebase de metodologia) | **decisão humana** antes de reprocessar |
| **AC** parada em 2026-03-01 | defasagem de ~6 meses (as outras UFs já divulgam 2026-08) | falha de ingestão a investigar |
| **PI** parada em 2026-06-01 | 2 meses de defasagem | mesma causa de AC (ver 3) |
| 8 UFs sem cotação | AL, AP, MS, RO, RS, SE, SP, TO | limitação de roadmap (LIM-38), **não** é defeito |

## 2. AM — valor repetido (forward-fill), não "dado corrompido"

> **Correção de diagnóstico (2026-09-30, após re-certificação).** A primeira
> versão deste documento chamou a série de AM de "queda implausível" e sugeriu
> rebase/metodologia. **A matemática está correta.** O defeito é de ingestão:
> **maio e junho repetem o valor de abril** e julho ressincroniza de uma vez.

Leitura da série real (AM · R1-N · `SEM_DESONERACAO`, `cub_mensal`):

| Competência | `valor_m2` | `variacao_mensal_pct` |
|---|---|---|
| 2026-04 | 3897,23 | +1,57% |
| 2026-05 | 3897,23 | **0,00%** ← repetido |
| 2026-06 | 3897,23 | **0,00%** ← repetido |
| 2026-07 | 3685,04 | −5,44% (ressincronização) |

Em todas as transições a variação declarada confere com
`(valor_mês / valor_mês_anterior − 1)`. O −12,44% do `CSL-16-A` é o **acúmulo**
da defasagem até a ressincronização — não erro de cálculo.

**Detector implementado (Onda D, B-01):** `autocub/processor/repeticao.py`
identifica 2+ meses consecutivos com o mesmo valor por
(UF, padrão, desoneração) e marca `dados_provisorios: true` +
`alerta_valor_repetido` **sem descartar** (descartar viraria buraco na série).
Rodado contra o banco em 2026-09-30: **6 registros de AM** (3 em maio, 3 em
junho) e **zero** em outras UFs — ou seja, o problema é de AM, como neste
diagnóstico.

`variacao_mensal_pct = 0,00` está dentro da faixa da guarda de sanidade
(|var| > 5%), então ela **não** detectava este caso — daí um detector próprio.

**O que NÃO foi feito (decisão humana pendente):** reprocessar AM de 2026-05 a
2026-07 contra a fonte do Sinduscon-AM. Exige backup e autorização, e depende
de confirmar se a publicação também traz a defasagem.

### 2b. Registros de AM com valor repetido (lidos do banco, 2026-09-30)



Variação mensal (2026-07) por UF, `SEM_DESONERACAO`:

```
AM| 19 reg | min -12.44% | max  2.68%   <-- REVISAR
RN| 19 reg | min  -0.65% | max  1.00%
CE| 19 reg | min  -0.64% | max  2.37%
DF| 19 reg | min  -0.53% | max  2.82%
PE| 19 reg | min  -0.59% | max  0.09%
GO| 19 reg | min  -0.46% | max  0.29%
PA| 19 reg | min  -0.22% | max  2.20%
MA| 19 reg | min  -0.20% | max  0.22%
RJ| 19 reg | min   0.00% | max  0.36%
MG| 38 reg | min   0.05% | max  2.01%
PR| 38 reg | min   0.07% | max  4.33%
PB| 19 reg | min   0.11% | max  0.55%
RR| 19 reg | min   0.13% | max  0.45%
MT| 19 reg | min   0.25% | max  1.29%
SC| 19 reg | min   0.86% | max  1.11%
BA| 19 reg | min   1.05% | max  1.68%
ES| 19 reg | min   1.99% | max  2.22%
```

Os cinco piores registros de AM (junho → julho):

Valores lidos direto de `cub_mensal` em 2026-09-30 (`SEM_DESONERACAO`):

| Padrão | 2026-06 | 2026-07 | Variação |
|---|---|---|---|
| CAL-8-A | 3873,34 | 3391,47 | −12,44% |
| CSL-16-A | 4857,75 | 4273,52 | −12,03% |
| CSL-8-A | 3642,75 | 3227,09 | −11,41% |
| R8-A | 4284,50 | 3838,42 | −10,41% |
| R1-A | 5371,36 | 4883,43 | −9,08% |

**Observações que orientam a investigação:**

1. A queda é **uniforme** em todos os padrões e nas **duas** desonerações
   (COM_DESONERACAO cai até −13,11%) — não é troca de variante nem erro de
   unidade em um registro isolado.
2. O padrão `A` (desonerado) cai **mais** que o `N` (não desonerado) em todos
   os pares comparáveis (ex.: R8-A −10,41% vs. R8-N −4,85%). Isso sugere
   **rebase da tabela debase** ou mudança de metodologia do Sinduscon-AM, não
   erro de digitação.
3. Nenhuma outra UF do CBIC caiu mais de 4,33% no mesmo mês.

**Decisão pendente (humana):** comparar a tabela publicada pelo Sinduscon-AM
(boletim de julho/2026) com o que foi ingerido. Se a publicação também traz a
queda, o dado está correto e a anomalia é real (implicando revisão de todo
orçamento que use AM/2026-07). Se a publicação não traz, é erro de carga e o
caminho é reprocessar **com backup** e guarda de sanidade ativa.

## 3. AC e PI — defasagem de ingestão

| UF | Última referência | Defasagem (setembro/2026) |
|---|---|---|
| AC | 2026-03-01 | ~6 meses |
| PI | 2026-06-01 | ~3 meses |
| demais 17 UFs com dado | 2026-07-01 a 2026-08-01 | ok |

**Sintoma:** a UF tem sindicato cadastrado e histórico até 2026-03, mas a
ingestão parou. `etl_execucoes` mostra a última execução registrada em
**2024-11** (id 2795) — ou seja, o histórico de execuções **não reflete** as
cargas que produziram 2026-05..2026-08 (elas vieram por outro caminho, provavelmente
reprocesso/manual), então o log não serve para diagnosticar a causa.

**Investigar:**
1. Se o adapter/URL para AC e PI ainda resolve no CBIC (mudança de URL, mudança
   de formato do PDF, sinduscon desativado).
2. Se o downloader registra a falha em log (o `etl_execucoes` não mostra FALHA
   para essas UFs).
3. Reprocessar AC/PI após confirmar a causa, **com backup** — o pipeline aceita
   `force_download`/`force=true`.

## 4. Vacinas já implementadas nesta fase (Onda 4)

- **Guarda de sanidade na ingestão** (`autocub/processor/sanity.py`): registro
  com `|variacao_mensal_pct| > CUB_VARIACAO_MAX_PCT` (padrão **5%**) não entra
  em `cub_mensal`; fica em **quarentena** e a execução é gravada como
  `SUCESSO_QUARENTENA` com log de amostra. Não há correção automática — a causa
  é sempre decisão humana.
  - `etl_execucoes.status` é `varchar(20)`: o nome do status foi mantido curto
    por isso; um *widen* para `varchar(30)` exigiria migração (pendente).
- **Cobertura visível** (`cub_health.cobertura`): `ufs_com_dado`, `ufs_total`,
  `ufs_sem_dado`, `ufs_com_sindicado_sem_cotacao`, `ultima_atualizacao` — a
  lacuna fica declarada antes de o cliente perguntar.
- **Envelope de vazio** (C-01): toda tool CUB que volta sem linhas responde
  `{items: [], sem_dados, motivo, ultima_referencia_disponivel}` em vez de
  `content: []`.

Com a guarda ativa, uma repetição do caso AM em uma execução futura **não**
entra em silêncio: o operador vê a quarentena e decide.

## 5. Referências

- Certificação funcional 2026-09-30 (relatório recebido), veredito por item em
  `docs/projects/STORY-MCP-007-certificacao-funcional-mcp-custo.md` (casa).
- Story desta fase: `docs/PLAN-auditoria-mcp-p0.md`.
- Lim-38: nota de cobertura já presente nas respostas (decisão 2026-09-30).
