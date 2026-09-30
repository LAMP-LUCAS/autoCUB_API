from decimal import Decimal

from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field, TypeAdapter, validate_call

from autocub_mcp import envelope
from autocub_mcp.auth import resolve_api_key
from autocub_mcp.cache import cache_key
from autocub_mcp.tools.tier_1 import get_cache, get_client


class AreaItemInput(BaseModel):
    ambiente: str
    area_real_m2: Decimal = Field(gt=0)
    fator_ponderacao: Decimal | None = Field(default=None, ge=0, le=2)


class CalculoAreaRequest(BaseModel):
    itens: list[AreaItemInput] = Field(min_length=1)
    cub_m2: Decimal | None = Field(default=None, gt=0)
    uf: str | None = None
    codigo_padrao: str | None = None


# STORY-MCP-007/C-04: `payload` é SEMPRE objeto. A união com `list[AreaItemInput]`
# aceitava a forma-lista, que perde `uf`/`cub_m2` — o cálculo voltava com
# `custo_estimado_total: null` e nenhuma explicação (a API agora responde 422).
AreaPayload = CalculoAreaRequest


@validate_call
async def cub_calc_area(payload: AreaPayload, ctx: Context | None = None) -> dict | list:
    """Calcula área equivalente (NBR 12.721) e o custo estimado da obra.

    **Tipagem (ADR 009):** todo valor numérico da resposta é JSON **number**
    (`float`) — nunca string. Some e multiplique direto; datas seguem string
    ISO. `Decimal` só existe dentro do cálculo, não na resposta.

    **`uf` é obrigatória para orçar** (B-06): sem `cub_m2` nem `uf`, a resposta
    vem com `erro: CUB_NAO_INFORMADO` e `motivo` explicando o que enviar. Sem
    CUB para a UF, vem `erro: CUB_INDISPONIVEL_PARA_UF` + `motivo` +
    `ufs_com_cub_mais_proximas` — nunca `custo_estimado_total: null` mudo.

    O payload é sempre um objeto `CalculoAreaRequest` (a forma-lista foi
    removida: perdia a UF e o cálculo voltava sem orçamento).
    """
    api_key = resolve_api_key(ctx)
    adapter: TypeAdapter[AreaPayload] = TypeAdapter(AreaPayload)
    body = adapter.dump_python(payload, mode="json", exclude_unset=True)
    key = cache_key("POST:/v1/calc/area", {"body": body}, api_key=api_key)
    resultado = await get_cache().get_or_fetch(
        key, lambda: get_client().post("/v1/calc/area", json=body, api_key=api_key)
    )
    consulta = {"uf": (payload.uf or "").upper() or None, "recurso": "/v1/calc/area"}
    if not isinstance(resultado, dict):
        return resultado

    # "Sem dado" = o orçamento é explicitamente nulo (`custo_estimado_total: null`)
    # ou a API sinalizou `erro`. Se o campo AUSENTAR, tratamos como resposta com
    # dado — API antiga não deve ser lida como falha.
    sem_orcamento = (
        ("custo_estimado_total" in resultado and resultado["custo_estimado_total"] is None)
        or bool(resultado.get("erro"))
    )
    if sem_orcamento:
        # Sem CUB resolvível o cálculo de área continua válido, mas o orçamento
        # não existe. O envelope único entra COMPLEMENTANDO os campos próprios
        # (erro/motivo/ufs_com_cub_mais_proximas, exigidos pelo claim C-04).
        codigo = resultado.get("erro") or "CUB_NAO_PUBLICADO_POR_UF"
        env = await envelope.sem_dado(consulta=consulta, codigo=codigo, ctx=ctx)
        env.update(resultado)                      # preserva o cálculo e o C-04
        env["status"] = "sem_dado"
        env["disponivel"] = False
        env["itens"] = env.get("itens") or []
        env["total"] = 0
        return env

    return await envelope.com_vigencia(resultado, consulta, ctx)
