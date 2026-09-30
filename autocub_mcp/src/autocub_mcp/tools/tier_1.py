from urllib.parse import quote

from pydantic import validate_call
from mcp.server.fastmcp import Context

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


async def _get(path: str, params: dict, ctx: Context | None) -> dict | list:
    api_key = resolve_api_key(ctx)
    params = {k: v for k, v in params.items() if v is not None}
    key = cache_key(path, params, api_key=api_key)
    return await get_cache().get_or_fetch(
        key, lambda: get_client().get(path, params=params or None, api_key=api_key)
    )


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

    LIM-38 (decisão 2026-09-30): UF brasileira válida sem adapter/dado
    publicado **responde** com `nota_lim38` ("dado ainda não disponibilizado
    pelo CBIC; equipe procurando solução") em vez de propagar erro — o claim
    do gate cobre a sinalização, nunca a cobertura.
    """
    try:
        return await _get(
            f"/v1/cub/{segment(uf)}",
            {"ano": ano, "mes": mes, "desoneracao": desoneracao, "sinduscon_id": sinduscon_id},
            ctx,
        )
    except NotFoundError as exc:
        # Marcador "LIM-38" vem no `detail` da API (repassado pelo client);
        # 404 de outro tipo segue como erro.
        if "LIM-38" in str(exc):
            return {
                "uf": uf.upper(),
                "encontrado": False,
                "nota_lim38": NOTA_LIM38,
                "motivo": str(exc),
            }
        raise


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
    )


@validate_call
async def cub_padroes_list(
    categoria: str | None = None, padrao_acabamento: str | None = None, ctx: Context | None = None
) -> dict | list:
    return await _get(
        "/v1/padroes", {"categoria": categoria, "padrao_acabamento": padrao_acabamento}, ctx
    )


@validate_call
async def cub_sinduscons_list(
    uf: str | None = None,
    regiao: str | None = None,
    ativo_apenas: bool = True,
    ctx: Context | None = None,
) -> dict | list:
    return await _get(
        "/v1/sinduscons", {"uf": uf, "regiao": regiao, "ativo_apenas": ativo_apenas}, ctx
    )


@validate_call
async def cub_health(ctx: Context | None = None) -> dict | list:
    return await _get("/v1/health", {}, ctx)
