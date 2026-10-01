# Diagnóstico de dados CUB — AM, AC, PI (STORY-MCP-007/C-03)

> Medido em 2026-09-30 contra o banco de produção (`cub`).
> **Nenhum dado foi reprocessado** — e o dry-run de 2026-10-01 provou que
> reprocessar seria operação sem efeito: a base está fiel ao PDF publicado
> (ver 2c). Backup foi feito e **verificado por restauração**; nada foi gravado.

## 1. Resumo

| Achado | Situação | Natureza |
|---|---|---|
| **AM** valor repetido em 2026-05/06 | **causa FECHADA (2026-10-01): defeito da FONTE** — o Sinduscon-AM publicou junho com os valores de maio; nossa carga está fiel (ver 2c) | pergunta ao sindicato (ação externa) |
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

### 2c. CAUSA-RAIZ FECHADA (2026-10-01): o índice é MANTIDO pela fonte, não corrompido

Backup + dry-run foram executados (autorizados pelo usuário). O dry-run parseou
os PDFs da fonte (Sinduscon-AM, `sinduscon_id=5`) e comparou com o banco, **sem
gravar nada**:

| Competência | PDF (fonte) CAL-8-A | Banco | PDF (fonte) R1-N | Banco | Bate? |
|---|---|---|---|---|---|
| 2026-04 | 3873,25 | 3873,25 | 3897,23 | 3897,23 | ✅ 19/19 |
| 2026-05 | 3873,34 | 3873,34 | 3897,23 | 3897,23 | ✅ 19/19 |
| 2026-06 | 3873,34 | 3873,34 | 3897,23 | 3897,23 | ✅ 19/19 |
| 2026-07 | 3391,47 | 3391,47 | 3685,04 | 3685,04 | ✅ 19/19 |

Comparação **entre os próprios PDFs** (mesma série, dentro da fonte):

| Par | Padrões com valor idêntico no PDF |
|---|---|
| 2026-05 vs 2026-04 | 3/19 |
| **2026-06 vs 2026-05** | **19/19** ← a repetição está no arquivo publicado |
| 2026-07 vs 2026-06 | 0/19 (ressincronização) |

Os `sha256` dos quatro PDFs são distintos (`08be7af9…`, `98c5c0b4…`, `b1a30f36…`,
`4e5b0a34…`), ou seja, não é o mesmo arquivo re-servido: o **Sinduscon-AM
publicou a competência de junho com os valores de maio**.

**Conclusão:** a nossa carga está fiel à fonte. O `upsert` de 2026-05..07
gravaria exatamente os mesmos valores — **reprocessar é operação sem efeito**.
Nada foi gravado (checksum do acervo inalterado: `9a05de34…` antes e depois).

### 2d. VERIFICAÇÃO DIRETA NA FONTE (2026-10-01) e correção do alarme

A evidência acima comparava a base com o **cache** (baixado em 03/09). Para
fechar a lacuna, os PDFs foram baixados **direto do `cub.org.br`** no dia:

| Competência | Fonte ao vivo (baixada 01/10) | Cache | Banco | Bate? |
|---|---|---|---|---|
| 2026-05 | sha `5aaf71eb…`, R1-N = 3897,23 | 3897,23 | 3897,23 | ✅ 19/19 |
| 2026-06 | sha `fac773eb…`, R1-N = 3897,23 | 3897,23 | 3897,23 | ✅ 19/19 |

Os `sha` do download atual diferem do cache porque o CBIC **regera** o arquivo a
cada visita — mas o **conteúdo é o mesmo**. Confirmação definitiva: **o
Sinduscon-AM publica 3.897,23 em maio e em junho**.

**Consequência de projeto (decisão do usuário, 2026-10-01):** o alerta de
"dado provisório" foi **removido**. Ele se apoiava na hipótese de forward-fill
nosso, que a verificação refutou; mantê-lo injectava desconfiança em número
oficial correto e podia fazer o agente recusar valor válido — o risco
inverso, tão grave quanto o original.

- Respostas das tools: **nenhuma marcação**. O valor chega com `vigencia` e
  pronto para orçamento.
- `cub_health.cobertura.series_indice_estavel`: diagnóstico **factual** para o
  operador (quais séries mantiveram o índice), sem veredito.
- Log da ETL: informativo, nível `INFO`.
- `SERIA_SINCRONIZADA_COM_ATRASO` saiu do catálogo de motivos (nunca foi
  emitida e nomeava um defeito inexistente).

**O que realmente protegeria** contra forward-fill nosso (o risco original) não
é um alarme, é **verificação**: comparar o valor ingerido com o PDF da fonte
na hora da carga — foi exatamente o que o dry-run fez (19/19) e o que a ETL
deveria fazer por padrão. É a evolução natural deste detector.

O item B-01 fica **encerrado como defeito de fonte**, com duas ações:

1. **Pergunta para o Sinduscon-AM:** a publicação de 2026-06 deveria ter
   repetido os valores de 2026-05? Se sim, é o índice que parou; se não, é
   republicação indevida e a fonte precisa republicar.
2. **Enquanto isso, nada muda no código:** o detector de valor repetido e o
   `alerta` de série provisória já marcam AM corretamente (o agente orça com o
   aviso) e o próximo ciclo de republicação da fonte resolve sozinho.

**Backup mantido** como rede de segurança para o próximo ciclo natural da ETL
(não havia necessidade de restauração, mas o dump verificado fica disponível):
- `backups/cub_20261001_0704_pre-reprocess-AM.sql` (1,6 MB, sha256 `6851bc81…`)
  — **verificado por restauração**: md5 do conteúdo de `cub_mensal` idêntico ao
  produção (`9a05de34…`), 5/5 tabelas com contagem igual
- `backups/cub_AM_2026-05_07_pre-reprocess.csv` — as 114 linhas alvo em CSV legível

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

## 2e. PROTEÇÃO IMPLEMENTADA (2026-10-01): verificação, não alarme

O alerta de "provisório" foi removido (2d). A proteção que o substitui é
**conferir a fonte na ingestão** — `autocub/processor/conferencia.py`, ligado
em `process_single_cub_report`:

- **C1 · período declarado × pedido** — o rótulo do próprio PDF é conferido antes
  de gravar. Tri-estado: `confere` / `divergente` / `indeterminado`. Divergente
  **não grava** (fato: arquivo de outra competência); indeterminado grava e
  registra que não deu para conferir (nunca bloqueia por ignorância).
  Medido em 1.144 PDFs: 1.117 confere · 22 divergentes (cache órfão, nunca
  ingerido) · 5 indeterminados.
- **C2 · gravação × PDF** — relê do banco só o que gravou e compara (único check
  que pega erro de chave). Divergência vira `CONFERIU_DIVERGENTE`.
- **C3 · índice mantido** — o detector existente, agora como FATO.
- Resultado: `etl_execucoes` (status + mensagem, **sem DDL**) + JSON de
  auditoria em `data/conferencia/`; exposto em `cub_health.cobertura.conferencia_da_fonte`
  (claim de gate §B-01x).

Isso converte a lição em mecanismo: **só há sinal quando há fato medido na
fonte**. Em AM, onde a repetição é o índice oficialmente mantido, nada é
sinalizado; um arquivo de competência errada, se baixado, é barrado na hora.

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
