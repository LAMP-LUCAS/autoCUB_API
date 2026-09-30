from decimal import Decimal

from pydantic import BaseModel, Field, TypeAdapter, validate_call
from mcp.server.fastmcp import Context

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
    api_key = resolve_api_key(ctx)
    adapter: TypeAdapter[AreaPayload] = TypeAdapter(AreaPayload)
    body = adapter.dump_python(payload, mode="json", exclude_unset=True)
    key = cache_key("POST:/v1/calc/area", {"body": body}, api_key=api_key)
    return await get_cache().get_or_fetch(
        key, lambda: get_client().post("/v1/calc/area", json=body, api_key=api_key)
    )
