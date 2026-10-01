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
- **Contrato único de "sem dado" (STORY-MCP-007, Onda A):** toda tool
  responde o **mesmo** envelope quando não há dado —
  `{status: "sem_dado", disponivel: false, consulta, motivo{codigo, descricao,
  natureza}, vigencia, alternativas, orientacao, itens: [], total: 0}`.
  O agente não precisa decorar um formato por tool.
  - `natureza` diz quem resolve: `limitacao_externa` (CBIC/sindicato não
    publica), `ingestao_pendente` (existe, não foi carregado), `defasagem`
    (existe, para período anterior), `parametro_invalido`.
  - `alternativas` + `orientacao.texto` transformam "não tenho" em "use isto".
  - Nunca `content: []`; nunca erro genérico; `correlation_id` preservado.
  - **LIM-38 (cobertura 19/27 UFs — roadmap, não defeito):** UF brasileira sem
    CUB publicado responde `motivo.codigo = CUB_NAO_PUBLICADO_POR_UF`. O texto
    que cita o identificador do ticket fica em `nota_interna` (rastreabilidade
    do servidor) — **jargão interno não vai para o corpo do cliente** (B-05).
- **Envelope nas duas direções (P1-2):** com dado, a resposta também é o mesmo
  envelope — `{status: "ok", disponivel: true, consulta, vigencia, items, total}`
  (mais os campos próprios da tool). Coerência do contrato tem precedência
  sobre a forma de lista (decisão do usuário 2026-09-30): o agente escreve
  contra um formato estável nos dois caminhos.
- **Índice mantido não é defeito:** se o mesmo valor aparece em competências
  seguidas, é porque a **fonte oficial o mantém** (verificado em 2026-10-01 no
  cub.org.br: o Sinduscon-AM publica 3.897,23 em maio e em junho). As respostas
  **não** marcam nada nesse caso — o valor é o oficial e deve ser usado. Se
  quiser o diagnóstico, `cub_health.cobertura.series_indice_estavel` diz quais
  séries mantiveram o índice.
- **Provenance em UF multi-sindicato (P0-2):** `cub_get_uf` traz **um item por
  sindicato ativo**, ordenados por competência **decrescente**, e o item que a
  API usa por default (§5.1) vem primeiro com `recomendado: true` +
  `motivo_recomendacao`. Não escolha a praça "por posição na lista": em MG são
  3, com competências diferentes (2026-08, 2026-07, 2026-06).
- **Paginação de `cub_latest`:** o acervo tem ~19 registros por UF, então
  `limit=50` devolve só as primeiras UFs. Com `com_meta=true` a resposta traz
  `meta_navegacao{total, skip, limit, has_more}`; sem ele, você **não sabe se
  truncou** — nesse caso use `limit=0` (acervo completo).
- **Vigência (B-03):** toda resposta **com dado** traz
  `vigencia{vigente, meses_de_atraso, ultima_publicacao_conhecida}` —
  medida contra a competência mais recente do acervo. Em resposta em forma de
  lista (ex.: `cub_latest`) a vigência vem **por item**; a lista plana é
  contrato do LIM-38 para UF coberta e não vira envelope.
  - `vigente: false` + `alerta` = o número é antigo (AC responde 2026-03
    enquanto o acervo tem 2026-08). Confirme a vigência antes de orçar.

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
