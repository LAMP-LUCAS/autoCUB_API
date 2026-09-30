from urllib.parse import quote

from mcp.server.fastmcp import Context
from pydantic import validate_call

from autocub_mcp import envelope
from autocub_mcp.auth import resolve_api_key
from autocub_mcp.cache import CacheManager, cache_key
from autocub_mcp.client import APIClient, NotFoundError
from autocub_mcp.lim38 import NOTA_LIM38

_client: APIClient | None = None
_cache: CacheManager | None = None


def get_client() -> APIClient:
    global _client
    if _client is None:
        _client = APIClient()
    return _client


def get_cache() -> CacheManager:
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache


async def close_resources() -> None:
    global _client, _cache
    try:
        if _client is not None:
            await _client.close()
    finally:
        _client = None
        if _cache is not None:
            await _cache.close()
        _cache = None


def segment(value: str) -> str:
    if not value or value in (".", "..") or any(c in value for c in "/\\?#%"):
        raise ValueError("Invalid path segment")
    return quote(value.upper(), safe="")


async def _get(
    path: str,
    params: dict,
    ctx: Context | None,
    *,
    consulta: dict | None = None,
) -> dict | list:
    """Choke point do contrato (STORY-MCP-007, Onda A).

    Três estados, nunca misturados (ADR 010):

    * **com dado** → a resposta + ``vigencia`` (o agente sabe se é atual);
    * **sem dado** → envelope único ``{status, disponivel, consulta, motivo,
      vigencia, alternativas, orientacao, itens: [], total: 0}``;
    * **erro** → exceção nomeada com ``correlation_id``.

    Antes desta onda, 5 tools devolviam texto puro com ``isError=true`` para um
    dado que apenas não existe — e framework de agente trata ``isError`` como
    sinal de retry.
    """
    api_key = resolve_api_key(ctx)
    params = {k: v for k, v in params.items() if v is not None}
    consulta = {**(consulta or {}), "recurso": path, "parametros": params or None}
    key = cache_key(path, params, api_key=api_key)
    try:
        resultado = await get_cache().get_or_fetch(
            key, lambda: get_client().get(path, params=params or None, api_key=api_key)
        )
    except NotFoundError as exc:
        # 404 da API vira "sem dado" classificado — nunca erro genérico. O
        # marcador LIM-38 no `detail` diz que a UF é brasileira sem adapter.
        return await envelope.sem_dado(
            consulta=consulta,
            codigo=_classificar_404(str(exc)),
            ctx=ctx,
            nota_interna=_nota_interna_404(str(exc)),
        )

    if envelope.e_vazio(resultado):
        return await envelope.sem_dado(
            consulta=consulta,
            codigo=await _classificar_vazio(consulta, resultado, ctx),
            ctx=ctx,
            nota_interna=envelope.nota_interna_do_api(resultado),
        )
    return await envelope.com_vigencia(resultado, consulta, ctx)


def _classificar_404(mensagem: str) -> str:
    """404 → código do catálogo. O marcador LIM-38 (detail da API) distingue
    'UF sem adapter' de 'sindicado não cadastrado'."""
    if "LIM-38" in mensagem:
        return "CUB_NAO_PUBLICADO_POR_UF"
    return "SEM_SINDUSCON_CADASTRADO"


def _nota_interna_404(mensagem: str) -> dict | None:
    """Rastreabilidade interna SEM vazar jargão para o cliente (B-05).

    O texto com o identificador de ticket (`LIM-38`) fica aqui e no log do
    servidor; o corpo da resposta fala linguagem de domínio.
    """
    if "LIM-38" not in mensagem:
        return None
    return {"referencia": "LIM-38", "texto": NOTA_LIM38}


async def _classificar_vazio(consulta: dict, resultado: object, ctx) -> str:
    """Vazio (200 sem linhas) → código do catálogo.

    UF que **não aparece** no acervo é limitação externa (não publica); UF que
    aparece mas não tem o período é ingestion pendente — são coisas diferentes
    e a natureza do motivo muda (`limitacao_externa` x `ingestao_pendente`).
    """
    uf = (consulta.get("uf") or "").upper()
    if uf:
        snap = await envelope.snapshot(ctx)
        if uf not in snap.get("ufs", {}):
            return "CUB_NAO_PUBLICADO_POR_UF"
        return "SEM_COTACAO_PARA_O_PERIODO"
    if consulta.get("codigo_padrao"):
        return "PADRAO_NAO_DISPONIVEL"
    return "SEM_COTACAO_PARA_O_PERIODO"


@validate_call
async def cub_get_uf(
    uf: str,
    ano: int | None = None,
    mes: int | None = None,
    desoneracao: str = "SEM_DESONERACAO",
    sinduscon_id: int | None = None,
    ctx: Context | None = None,
) -> dict | list:
    """Cotações da UF no contexto informado.

    **Contrato único (STORY-MCP-007):** com dado → lista de cotações, cada uma
    com `vigencia`; sem dado → envelope `{status: "sem_dado", disponivel: false,
    motivo{codigo, descricao, natureza}, vigencia, alternativas, orientacao}`.
    UF brasileira sem CUB publicado (LIM-38) também responde envelope — o
    identificador do ticket fica em `nota_interna`, nunca no texto do cliente.
    """
    return await _get(
        f"/v1/cub/{segment(uf)}",
        {"ano": ano, "mes": mes, "desoneracao": desoneracao, "sinduscon_id": sinduscon_id},
        ctx,
        consulta={"uf": uf.upper(), "ano": ano, "mes": mes, "desoneracao": desoneracao},
    )


@validate_call
async def cub_latest(
    uf: str | None = None,
    desoneracao: str = "SEM_DESONERACAO",
    limit: int = 50,
    ctx: Context | None = None,
) -> dict | list:
    """Cotações mais recentes com origem territorial (UF, Sinduscon, Região).

    §5.6: paginado — `limit` default 50; `0` = sem limite (payload completo,
    use com moderação; sem `uf` o blob completo estoura a janela do agente).

    LIM-38: UF brasileira válida sem adapter/dado publicado devolve o
    envelope `{uf, items: [], nota_lim38}` em vez de lista vazia — a API
    sinaliza e esta tool apenas repassa (responder > `[]`)."""
    return await _get(
        "/v1/cub/latest",
        {"uf": uf.upper() if uf else uf, "desoneracao": desoneracao, "limit": limit},
        ctx,
        consulta={"uf": uf.upper() if uf else None, "desoneracao": desoneracao},
    )


@validate_call
async def cub_panorama(
    uf: str,
    ano: int | None = None,
    mes: int | None = None,
    desoneracao: str = "SEM_DESONERACAO",
    sinduscon_id: int | None = None,
    ctx: Context | None = None,
) -> dict | list:
    # §5.8: canônica aponta para a rota REST canônica (/dash); a rota legada
    # /panorama continua servida pela API para compatibilidade.
    return await _get(
        f"/v1/cub/{segment(uf)}/dash",
        {"ano": ano, "mes": mes, "desoneracao": desoneracao, "sinduscon_id": sinduscon_id},
        ctx,
        consulta={"uf": uf.upper(), "ano": ano, "mes": mes, "desoneracao": desoneracao},
    )


@validate_call
async def cub_dash(
    uf: str,
    ano: int | None = None,
    mes: int | None = None,
    desoneracao: str = "SEM_DESONERACAO",
    sinduscon_id: int | None = None,
    ctx: Context | None = None,
) -> dict | list:
    return await _get(
        f"/v1/cub/{segment(uf)}/dash",
        {"ano": ano, "mes": mes, "desoneracao": desoneracao, "sinduscon_id": sinduscon_id},
        ctx,
        consulta={"uf": uf.upper(), "ano": ano, "mes": mes, "desoneracao": desoneracao},
    )


@validate_call
async def cub_impacto_desoneracao(
    uf: str,
    ano: int | None = None,
    mes: int | None = None,
    sinduscon_id: int | None = None,
    ctx: Context | None = None,
) -> dict | list:
    return await _get(
        f"/v1/cub/{segment(uf)}/impacto-desoneracao",
        {"ano": ano, "mes": mes, "sinduscon_id": sinduscon_id},
        ctx,
        consulta={"uf": uf.upper(), "ano": ano, "mes": mes},
    )


@validate_call
async def cub_deson(
    uf: str,
    ano: int | None = None,
    mes: int | None = None,
    sinduscon_id: int | None = None,
    ctx: Context | None = None,
) -> dict | list:
    return await _get(
        f"/v1/cub/{segment(uf)}/deson",
        {"ano": ano, "mes": mes, "sinduscon_id": sinduscon_id},
        ctx,
        consulta={"uf": uf.upper(), "ano": ano, "mes": mes},
    )


@validate_call
async def cub_ranking(
    codigo_padrao: str = "R1-N",
    ano: int | None = None,
    mes: int | None = None,
    desoneracao: str = "SEM_DESONERACAO",
    ctx: Context | None = None,
) -> dict | list:
    return await _get(
        "/v1/cub/ranking",
        {
            "codigo_padrao": codigo_padrao.upper(),
            "ano": ano,
            "mes": mes,
            "desoneracao": desoneracao,
        },
        ctx,
        consulta={"codigo_padrao": codigo_padrao.upper(), "ano": ano, "mes": mes},
    )


@validate_call
async def cub_historico(
    uf: str,
    codigo_padrao: str,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    desoneracao: str = "SEM_DESONERACAO",
    sinduscon_id: int | None = None,
    ctx: Context | None = None,
) -> dict | list:
    return await _get(
        f"/v1/cub/{segment(uf)}/historico/{segment(codigo_padrao)}",
        {
            "ano_inicio": ano_inicio,
            "ano_fim": ano_fim,
            "desoneracao": desoneracao,
            "sinduscon_id": sinduscon_id,
        },
        ctx,
        consulta={"uf": uf.upper(), "codigo_padrao": codigo_padrao.upper(),
                  "ano": ano_inicio, "desoneracao": desoneracao},
    )


@validate_call
async def cub_comparativo(
    ufs: str,
    codigo_padrao: str = "R1-N",
    ano: int | None = None,
    mes: int | None = None,
    desoneracao: str = "SEM_DESONERACAO",
    ctx: Context | None = None,
) -> dict | list:
    return await _get(
        "/v1/cub/comparativo",
        {
            "ufs": ufs,
            "codigo_padrao": codigo_padrao.upper(),
            "ano": ano,
            "mes": mes,
            "desoneracao": desoneracao,
        },
        ctx,
        consulta={"ufs": ufs, "codigo_padrao": codigo_padrao.upper(),
                  "ano": ano, "mes": mes},
    )


@validate_call
async def cub_padroes_list(
    categoria: str | None = None, padrao_acabamento: str | None = None, ctx: Context | None = None
) -> dict | list:
    return await _get(
        "/v1/padroes", {"categoria": categoria, "padrao_acabamento": padrao_acabamento}, ctx,
        consulta={"catalogo": "padroes_nbr"},
    )


@validate_call
async def cub_sinduscons_list(
    uf: str | None = None,
    regiao: str | None = None,
    ativo_apenas: bool = True,
    ctx: Context | None = None,
) -> dict | list:
    return await _get(
        "/v1/sinduscons", {"uf": uf, "regiao": regiao, "ativo_apenas": ativo_apenas}, ctx,
        consulta={"uf": uf.upper() if uf else None, "regiao": regiao},
    )


@validate_call
async def cub_health(ctx: Context | None = None) -> dict | list:
    return await _get("/v1/health", {}, ctx, consulta={"catalogo": "saude_servico"})
