"""MCP resources do AutoCUB — §2.1 da auditoria MCP de custo.

A auditoria encontrou `list_mcp_resources() → {"resources": []}` nos três
servidores: nenhum schema legível por agente, tabela de códigos, referência
metodológica ou exemplo. Aqui o material é sintetizado de fontes já
existentes no repositório (nada é inventado):

- ``docs/GUIA_ENDPOINTS_E_REGRAS_DE_NEGOCIO.md`` — endpoints e regras;
- ``autocub/database/seed_data.py`` → ``PADROES_NBR12721`` — tabela de códigos;
- comportamento verificado ao vivo pela auditoria (§5.1, §5.6, §5.8, LIM-38).
"""

_PADROES_NBR12721 = """\
# Padrões NBR 12.721:2006 — tabela de códigos

Códigos aceitos em `codigo_padrao` (tools `cub_historico`, `cub_panorama`,
`cub_ranking`, `cub_comparativo`). Fonte: seed oficial do banco (`PADROES_NBR12721`).

| Código | Descrição |
|---|---|
| R1-B | Residência Unifamiliar - Padrão Baixo |
| R1-N | Residência Unifamiliar - Padrão Normal |
| R1-A | Residência Unifamiliar - Padrão Alto |
| R8-B | Residencial Multifamiliar - Padrão Baixo |
| R8-N | Residencial Multifamiliar - Padrão Normal |
| R8-A | Residencial Multifamiliar - Padrão Alto |
| R16-N | Residencial Multifamiliar - Padrão Normal (16 pav.) |
| R16-A | Residencial Multifamiliar - Padrão Alto (16 pav.) |
| PP-4-B | Prédio Popular - Padrão Baixo |
| PP-4-N | Prédio Popular - Padrão Normal |
| CAL-8-N | Comercial Andar Livre - Padrão Normal |
| CAL-8-A | Comercial Andar Livre - Padrão Alto |
| CSL-8-N | Comercial Salas e Lojas - Padrão Normal (8 pav.) |
| CSL-16-N | Comercial Salas e Lojas - Padrão Normal (16 pav.) |
| CSL-8-A | Comercial Salas e Lojas - Padrão Alto (8 pav.) |
| CSL-16-A | Comercial Salas e Lojas - Padrão Alto (16 pav.) |
| PIS | Projeto de Interesse Social |
| RP1Q | Residência Popular (1 Quarto) |

Convenção: sufixo `-B/-N/-A` = padrão Baixo/Normal/Alto; `R*` residencial,
`CAL`/`CSL` comercial, `PP` popular. Não todas as praças publicam todos os
códigos — a cobertura por UF aparece em `cub_health().fontes` (LIM-38).
"""

_GUIA = """\
# AutoCUB — guia de uso das tools (§2.1)

Material sintetizado de `docs/GUIA_ENDPOINTS_E_REGRAS_DE_NEGOCIO.md`.

## Fluxo recomendado

1. `cub_health()` — confira `stage` (produção declara `production`),
   `database` e o mapa `fontes` (UF → sindicatos que **efetivamente
   publicaram** cotação; só UF com dado publicado aparece — 19/27 hoje,
   limitação de roadmap LIM-38, não erro).
2. `cub_padroes_list()` / `cub_sinduscons_list()` — tabela de códigos e
   praças antes de filtrar.
3. `cub_panorama(uf)` — painel consolidado; o campo `fonte` identifica o
   sindicato publicador, a norma (NBR 12.721:2006) e o período do dado.
4. `cub_historico(uf, codigo_padrao, ...)` — série mensal. O resolvedor de
   praça é determinístico, mas em UF multi-sindicato (ex.: MG) passe
   `sinduscon_id` explícito para reprodutibilidade (auditoria §5.1).

## Convenções

- `uf`: sigla maiúscula (`MG`, `GO`).
- `codigo_padrao`: ver resource `autocub://referencia/padroes-nbr`.
- `desoneracao`: default `SEM_DESONERACAO` (valor vigente nas tools).
- `ano_inicio`/`ano_fim` (opcionais) recortam séries e rankings.
- Paginação: `cub_latest(limit=50)` é o default; `limit=0` devolve tudo
  (auditoria §5.6).
- **LIM-38 (cobertura 19/27 UFs — roadmap, não defeito):** UF brasileira
  sem adapter responde **sinalizada**, nunca `[]` silencioso —
  `cub_latest(uf)` devolve `{uf, items: [], nota_lim38}` (a nota diz que o
  dado ainda não foi disponibilizado pelo CBIC e que a equipe está
  procurando solução); `cub_get_uf` converte o 404 nessa mesma nota; as
  demais tools de UF respondem 404 com a nota no `detail`.

## Tools canônicas × aliases

| Tool canônica | Rota REST canônica | Alias deprecada (aviso 1 release) |
|---|---|---|
| `cub_panorama` | `/v1/cub/{uf}/dash` (alias `/panorama`) | `cub_dash` |
| `cub_deson` | `/v1/cub/{uf}/deson` (alias `/impacto-desoneracao`) | `cub_impacto_desoneracao` |

## Desoneração CPRB (Lei 12.546/2011)

`cub_deson(uf)` devolve a economia em R$/m² e % da desoneração da folha
(CPRB) para o padrão da UF — estudo tributário, não preço de referência.

## Exemplos

- `cub_panorama({"uf": "MG"})` → métricas + tipologias + árvore NBR + `fonte`
- `cub_historico({"uf": "MG", "codigo_padrao": "R1-N"})` → série mensal
- `cub_historico({"uf": "MG", "codigo_padrao": "R1-N", "sinduscon_id": 39})`
  → série reprodutível (praça fixada)
- `cub_latest({"limit": 50})` → cotações mais recentes paginadas
"""


def register_resources(server) -> None:
    """Registra os resources legíveis por agente no FastMCP (§2.1).

    ``server`` é a instância ``FastMCP`` devolvida por ``create_server()``;
    a função não importa o módulo ``server`` (evita import circular).
    """

    @server.resource(
        "autocub://guia/endpoints",
        name="Guia de endpoints e regras do CUB",
        description=(
            "Fluxo de uso das tools CUB: convenções (uf, codigo_padrao, "
            "sinduscon_id, paginação), tools canônicas × aliases deprecadas, "
            "health stage/fontes e exemplos de chamada."
        ),
        mime_type="text/markdown",
    )
    def guia_endpoints() -> str:
        return _GUIA

    @server.resource(
        "autocub://referencia/padroes-nbr",
        name="Padrões NBR 12.721:2006 (tabela de códigos)",
        description=(
            "Tabela dos 18 códigos de padrão de projeto (R1-B … RP1Q) com "
            "descrição e convenção de sufixos, aceitos pelas tools de série "
            "e ranking."
        ),
        mime_type="text/markdown",
    )
    def padroes_nbr() -> str:
        return _PADROES_NBR12721
