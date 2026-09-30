"""
Contrato único de resposta do AutoCUB — STORY-MCP-007 (Onda A).

Princípio do relatório de recertificação: **na ausência de dado, a API deve ser
sincera, informativa e orientativa.** Nunca número inventado, nunca branco,
nunca erro que não orienta o próximo passo.

Antes desta onda, "sem dado" tinha **4 formatos** em 13 tools: cinco devolviam
texto puro com ``isError=true`` (o agente recebia "falha" para um dado que
simplesmente não existe — e frameworks tratam ``isError`` como retry),
``cub_get_uf`` devolvia objeto solto e ``cub_sinduscons_list`` devolvia
envelope. O agente precisava decorar o comportamento de cada tool.

Agora há **um** contrato, com três estados que nunca se confundem:

======================  ========  ==============================================
Estado                  HTTP      Corpo
======================  ========  ==============================================
com dado                200       a resposta + ``vigencia``
sem dado                200       envelope completo (``disponivel: false``)
erro                    4xx/5xx   exceção nomeada com ``correlation_id``
======================  ========  ==============================================

Regras invioláveis (asseridas pelo gate da casa, claims §C-10/§C-11):

1. ``disponivel: false`` nunca vem com número — se há ``valor_m2``, então
   ``disponivel: true``.
2. ``motivo`` sempre presente, como **código + descrição + natureza**; nunca
   erro genérico.
3. ``natureza`` diz **quem pode resolver**: ``limitacao_externa`` (CBIC/sindicato
   não publica), ``ingestao_pendente`` (existe, não foi carregado),
   ``defasagem`` (existe, para período anterior) ou ``parametro_invalido``
   (parâmetro semanticamente inutilizável — entrada **malformada** continua
   sendo 400 nomeado, conforme ADR 010).
4. ``alternativas`` é obrigatório quando ``natureza != parametro_invalido``:
   é o que transforma "não tenho" em "use isto".
5. ``orientacao.texto`` é escrito para o humano que vai ler o orçamento.
6. Nunca ``content: []`` — sempre pelo menos um bloco.

Decisão de camada (2026-09-30): o contrato é do **MCP** (é o que o agente
consome); a API só ganha campos **aditivos**. Por isso as alternativas e a
vigência são derivadas de UMA chamada cacheada (``/v1/cub/latest?limit=0``),
sem custo extra por tool.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any, Optional

logger = logging.getLogger("autocub.envelope")

# ── catálogo de motivos (código → descrição, natureza) ───────────────────────
CATALOGO_MOTIVOS: dict[str, tuple[str, str]] = {
    "CUB_NAO_PUBLICADO_POR_UF": (
        "O sindicato desta UF não publica índice CUB e o CBIC não disponibiliza "
        "a série.",
        "limitacao_externa",
    ),
    "SEM_SINDUSCON_CADASTRADO": (
        "A UF não tem sindicato cadastrado com CUB.",
        "limitacao_externa",
    ),
    "SEM_COTACAO_PARA_O_PERIODO": (
        "A UF tem CUB publicado, mas não há cotação para o período pedido.",
        "ingestao_pendente",
    ),
    "REFERENCIA_DESATUALIZADA": (
        "A UF tem CUB, mas a última referência é anterior ao período pedido.",
        "defasagem",
    ),
    "PADRAO_NAO_DISPONIVEL": (
        "Este padrão NBR 12.721 não foi carregado para a UF.",
        "ingestao_pendente",
    ),
    "PARAMETRO_INVALIDO": (
        "Parâmetro semanticamente inutilizável (ex.: padrão NBR inexistente).",
        "parametro_invalido",
    ),
    "SERIA_SINCRONIZADA_COM_ATRASO": (
        "A série desta UF tem valores repetidos, aguardando ressincronização "
        "com a fonte oficial.",
        "ingestao_pendente",
    ),
}

STATUS_OK = "ok"
STATUS_SEM_DADO = "sem_dado"

# Marcas que o gate usa para reconhecer um envelope de "sem dado" (ver
# claim_cub_vazio_explicito — C-01, que não pode regredir).
MARCAS = ("status", "disponivel", "motivo", "alternativas", "orientacao", "nota_interna")


def e_vazio(resultado: object) -> bool:
    """`True` quando a API devolveu "sem dado" em qualquer uma das formas.

    Cobre as três que a API produz: lista vazia (`[]`), envelope com
    `items: []` (a sinalização LIM-38 do CUB) e o marcador `sem_dados`.
    """
    if isinstance(resultado, list):
        return not resultado
    if isinstance(resultado, dict):
        if resultado.get("sem_dados") is True:
            return True
        for chave in ("items", "result", "comparativo", "cotacoes"):
            valor = resultado.get(chave)
            if isinstance(valor, list) and not valor:
                return True
    return False


def nota_interna_do_api(resultado: object) -> dict | None:
    """Texto interno (LIM-38) que a API anexa — nunca vai direto ao cliente.

    B-05: identificador de ticket é rastreabilidade interna (log do servidor);
    o corpo da resposta fala linguagem de domínio, em `motivo`/`orientacao`.
    """
    if isinstance(resultado, dict) and resultado.get("nota_lim38"):
        return {"referencia": "LIM-38", "texto": resultado["nota_lim38"]}
    return None


def motivo(codigo: str) -> dict:
    """Bloco `motivo` do envelope, com descrição e natureza do catálogo."""
    descricao, natureza = CATALOGO_MOTIVOS.get(
        codigo, ("Dado indisponível para esta consulta.", "ingestao_pendente"),
    )
    return {
        "codigo": codigo,
        "descricao": descricao,
        "natureza": natureza,
        # espelho textual: quem lia `motivo` como string continua conseguindo
        "texto": descricao,
    }


# ── vigência (B-03) ──────────────────────────────────────────────────────────

def _mes(ref: Any) -> Optional[str]:
    """Normaliza uma referência (date, 'AAAA-MM', 'AAAA-MM-DD') em 'AAAA-MM'."""
    if ref is None:
        return None
    if isinstance(ref, date):
        return f"{ref.year:04d}-{ref.month:02d}"
    texto = str(ref).strip()
    return texto[:7] if len(texto) >= 7 else None


def meses_de_atraso(referencia: Any, mais_recente: Any) -> int:
    """Meses entre a referência e a competência mais recente conhecida."""
    ref, topo = _mes(referencia), _mes(mais_recente)
    if not ref or not topo:
        return 0
    ano_r, mes_r = int(ref[:4]), int(ref[5:7])
    ano_t, mes_t = int(topo[:4]), int(topo[5:7])
    return max(0, (ano_t - ano_r) * 12 + (mes_t - mes_r))


def vigencia(
    referencia: Any,
    mais_recente: Any = None,
    *,
    escopo: str = "cotacao",
) -> dict:
    """Vigência do dado consultado.

    ``vigente`` é verdadeiro só quando a referência é a mais recente conhecida
    **para aquele recorte** (UF ou escopo). O agente precisa disto antes de
    orçar: AC responde 2026-03 enquanto as demais UFs já publicaram 2026-08.
    """
    ref, topo = _mes(referencia), _mes(mais_recente)
    atraso = meses_de_atraso(ref, topo)
    if escopo == "catalogo_perene":
        # catálogo não "vigencia": é perene por natureza (NBR 12.721).
        return {
            "data_referencia": None,
            "vigente": True,
            "meses_de_atraso": 0,
            "ultima_publicacao_conhecida": None,
            "escopo": escopo,
            "nota": "Catálogo perene (NBR 12.721 / cadastro de sindicatos) — sem vigência mensal.",
        }
    vigente = ref is not None and (topo is None or ref >= topo)
    bloco = {
        "data_referencia": ref,
        "vigente": vigente,
        "meses_de_atraso": atraso,
        "ultima_publicacao_conhecida": topo or ref,
        "escopo": escopo,
    }
    if not vigente and atraso > 0:
        bloco["alerta"] = (
            f"Dado {atraso} mês(es) atrás da competência mais recente conhecida"
            + (f" ({topo})" if topo else "")
            + " — confirme a vigência antes de usar no orçamento."
        )
    return bloco


# ── snapshot de cobertura (1 chamada, cacheada) ──────────────────────────────

_snapshot_cache: dict = {"valor": None, "em": asyncio.Event()}


async def snapshot(ctx) -> dict:
    """Fatos de cobertura derivados de UMA chamada cacheada.

    ``/v1/cub/latest?limit=0`` devolve a cotação mais recente de cada sindicato;
    com ela sabemos quem tem dado, qual é a competência mais recente do acervo
    e — filtrando pelo período pedido — quais UFs têm CUB *naquele* período.
    """
    if _snapshot_cache["valor"] is not None:
        return _snapshot_cache["valor"]
    if not _snapshot_cache["em"].is_set():
        _snapshot_cache["em"].set()
    from autocub_mcp.auth import resolve_api_key
    from autocub_mcp.cache import cache_key
    from autocub_mcp.tools.tier_1 import get_cache, get_client

    api_key = resolve_api_key(ctx)
    # limit=0 pede o acervo completo: com ele sabemos o total real de registros
    # (navegação do B-04) sem estimar nada.
    chave = cache_key("/v1/cub/latest", {"limit": 0, "desoneracao": "SEM_DESONERACAO"},
                      api_key=api_key)
    try:
        registros = await get_cache().get_or_fetch(
            chave,
            lambda: get_client().get("/v1/cub/latest",
                                     params={"limit": 0, "desoneracao": "SEM_DESONERACAO"},
                                     api_key=api_key),
        )
    except Exception as exc:  # noqa: BLE001 - alternativas são acessórias
        logger.warning("snapshot de cobertura indisponível: %s", exc)
        registros = []
    if isinstance(registros, dict):
        registros = registros.get("items") or []

    por_uf: dict[str, str] = {}
    por_referencia: dict[str, list[str]] = {}
    padroes_por_uf: dict[str, set] = {}
    for item in registros or []:
        if not isinstance(item, dict):
            continue
        uf, ref = item.get("uf"), _mes(item.get("data_referencia"))
        if not uf or not ref:
            continue
        atual = por_uf.get(uf)
        if atual is None or ref > atual:
            por_uf[uf] = ref
        por_referencia.setdefault(ref, [])
        if uf not in por_referencia[ref]:
            por_referencia[ref].append(uf)
        if item.get("codigo_padrao"):
            padroes_por_uf.setdefault(uf, set()).add(item["codigo_padrao"])

    valor = {
        "ufs": por_uf,
        "por_referencia": por_referencia,
        "padroes_por_uf": padroes_por_uf,
        "referencia_mais_recente": max(por_uf.values()) if por_uf else None,
        "ufs_com_dado": sorted(por_uf),
        # total real de registros do acervo (B-04): o `limit=0` já traz tudo.
        "total_registros": _total_registros(registros),
    }
    _snapshot_cache["valor"] = valor
    return valor


def _total_registros(registros: object) -> int:
    """Contagem real dos registros recebidos no acervo (sem estimativa)."""
    return len(registros) if isinstance(registros, list) else 0


async def _alternativas(consulta: dict, snap: dict) -> dict:
    """Bloco `alternativas`: o que o agente pode fazer em vez de nada."""
    uf = (consulta.get("uf") or "").upper()
    periodo = _periodo_chave(consulta)
    ufs_periodo = snap.get("por_referencia", {}).get(periodo, []) if periodo else []
    padroes = sorted(snap.get("padroes_por_uf", {}).get(uf, set()))
    return {
        "ufs_com_dado": snap.get("ufs_com_dado", []),
        "ufs_com_cubo_mesmo_periodo": sorted(ufs_periodo),
        "meses_disponiveis_nesta_uf": sorted({_mes(r) for r in [] if r}) or None,
        "padroes_disponiveis": padroes or None,
        "periodo_consultado": periodo,
    }


def _periodo_chave(consulta: dict) -> Optional[str]:
    ano, mes = consulta.get("ano"), consulta.get("mes")
    if ano and mes:
        return f"{int(ano):04d}-{int(mes):02d}"
    return None


_ORIENTACAO = {
    "CUB_NAO_PUBLICADO_POR_UF": (
        "usar_uf_proxima",
        "Para orçar nesta UF use o CUB de uma UF com série ativa e registre em "
        "contrato que o índice é de UF diversa.",
        "O CUB da UF vizinha não cobre as particularidades de fundação e "
        "licitação da UF pedida.",
    ),
    "SEM_SINDUSCON_CADASTRADO": (
        "usar_uf_proxima",
        "Use o CUB de uma UF com série ativa e registre a referência cruzada "
        "em contrato.",
        "Índice de outra UF subestima custos próprios da região.",
    ),
    "SEM_COTACAO_PARA_O_PERIODO": (
        "usar_referencia_anterior",
        "Consulte a última referência disponível desta UF ou avance a "
        "ingestão do período.",
        "Valores de um período anterior não refletem o custo vigente.",
    ),
    "REFERENCIA_DESATUALIZADA": (
        "usar_referencia_anterior",
        "Use a competência mais recente desta UF e sinalize a defasagem no "
        "orçamento.",
        "Índice antigo subestima custos por correção monetária ao longo de 2026.",
    ),
    "PADRAO_NAO_DISPONIVEL": (
        "usar_padrao_da_uf",
        "Escolha um dos padrões com dado nesta UF (ver `padroes_disponiveis`).",
        "Aplicar um padrão de outra UF distorce a área equivalente.",
    ),
    "PARAMETRO_INVALIDO": (
        "corrigir_parametro",
        "Confira o parâmetro enviado (UF, padrão e período).",
        "Parâmetro inválido produz cálculo sem lastro.",
    ),
    "SERIA_SINCRONIZADA_COM_ATRASO": (
        "aguardar_ressincronizacao",
        "A série tem valores repetidos; confirme a data do último boletim da "
        "fonte antes de orçar.",
        "Valor repetido é sinal de republicação, não de estabilidade de preço.",
    ),
}


def _orientacao(codigo: str) -> dict:
    acao, texto, risco = _ORIENTACAO.get(
        codigo,
        ("consultar_documentacao", "Consulte a documentação da tool.", "Risco não avaliado."),
    )
    return {"acao_recomendada": acao, "texto": texto, "risco": risco}


# ── montagem do envelope ─────────────────────────────────────────────────────

async def sem_dado(
    *,
    consulta: dict,
    codigo: str,
    ctx,
    nota_interna: Optional[dict] = None,
    extras: Optional[dict] = None,
) -> dict:
    """Envelope completo de "sem dado" (ADR 010: ausência de dado ≠ erro)."""
    snap = await snapshot(ctx)
    bloco_motivo = motivo(codigo)
    uf = (consulta.get("uf") or "").upper()
    alternativas = await _alternativas(consulta, snap)
    # Período pedido sem ninguém: sugere o que existe.
    if not alternativas["ufs_com_cubo_mesmo_periodo"]:
        alternativas["ufs_com_cubo_mesmo_periodo"] = alternativas["ufs_com_dado"][:6]
    referencia_uf = snap.get("ufs", {}).get(uf)
    envelope = {
        "status": STATUS_SEM_DADO,
        "disponivel": False,
        "consulta": {k: v for k, v in consulta.items() if v is not None},
        "motivo": bloco_motivo,
        "vigencia": vigencia(
            referencia_uf, snap.get("referencia_mais_recente"),
            escopo="uf" if uf else "global",
        ),
        "alternativas": alternativas,
        "orientacao": _orientacao(codigo),
        "itens": [],
        "total": 0,
    }
    if nota_interna:
        envelope["nota_interna"] = nota_interna
    for chave, valor in (extras or {}).items():
        if valor is not None:
            envelope[chave] = valor
    return envelope


async def com_vigencia(corpo: Any, consulta: dict, ctx) -> Any:
    """Adiciona `vigencia` a uma resposta **com dado**.

    Resposta em forma de dicionário recebe o bloco no topo; resposta em forma de
    lista recebe **por item** — a lista plana é contrato do LIM-38 e não pode
    virar envelope sem quebrar o claim que exige lista para UF coberta.
    """
    snap = await snapshot(ctx)
    topo = snap.get("referencia_mais_recente")
    uf_consulta = (consulta.get("uf") or "").upper()

    # `vigente` é sempre medido contra a competência mais recente do ACERVO,
    # não contra a própria UF: AC responder 2026-03 num acervo que já tem
    # 2026-08 precisa aparecer como defasado (é o caso B-03 do relatório).
    # NÃO mutamos o objeto vindo do cache: devolvemos cópia (o cache é
    # compartilhado entre requisições e entre tools).
    if isinstance(corpo, list):
        # Catálogo perene (NBR 12.721 / cadastro de sindicatos) não tem
        # vigência mensal — declarar isso é melhor que inventar uma data.
        perene = bool(consulta.get("catalogo"))
        saida = []
        for item in corpo:
            if not isinstance(item, dict):
                saida.append(item)
                continue
            if perene:
                saida.append({**item, "vigencia": vigencia(None, None,
                                                            escopo="catalogo_perene")})
                continue
            alvo = (item.get("uf") or uf_consulta or "").upper()
            referencia = item.get("data_referencia") or snap.get("ufs", {}).get(alvo)
            saida.append({
                **item,
                "vigencia": vigencia(referencia, topo, escopo="uf" if alvo else "global"),
            })
        return saida

    if isinstance(corpo, dict):
        corpo = dict(corpo)
        referencia = corpo.get("data_referencia")
        if referencia is None and uf_consulta:
            referencia = snap.get("ufs", {}).get(uf_consulta)
        # catálogo perene (NBR 12.721 / cadastro de sindicatos) não tem
        # vigência mensal — declarar isso é melhor que inventar uma data.
        if referencia is None and consulta.get("catalogo"):
            escopo = "catalogo_perene"
        else:
            escopo = "uf" if uf_consulta else "global"
            if referencia is None:
                referencia = corpo.get("ultima_atualizacao") or topo
        if escopo == "catalogo_perene":
            corpo["vigencia"] = {
                "data_referencia": None,
                "vigente": True,
                "meses_de_atraso": 0,
                "ultima_publicacao_conhecida": None,
                "escopo": escopo,
                "nota": "Catálogo perene (NBR 12.721 / cadastro de sindicatos) — sem vigência mensal.",
            }
        else:
            corpo["vigencia"] = vigencia(referencia, topo, escopo=escopo)
    return corpo


def limpar_cache_snapshot() -> None:
    """Usado pelos testes: zera o snapshot memoizado no processo."""
    _snapshot_cache["valor"] = None
    _snapshot_cache["em"].clear()
