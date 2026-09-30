from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.server.fastmcp import Context

from autocub_mcp.tools import tier_2


def context_with_key(key: str):
    request = SimpleNamespace(headers={"x-api-key": key})
    return Context(request_context=SimpleNamespace(request=request))


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"itens": []},
        [{"ambiente": "Sala", "area_real_m2": 0}],
        [{"ambiente": "Sala", "area_real_m2": 10, "fator_ponderacao": 3}],
    ],
)
async def test_calc_area_invalid(payload):
    with pytest.raises(ValueError):
        await tier_2.cub_calc_area(payload=payload)


async def test_calc_area_list_and_cache_partition(monkeypatch):
    client = AsyncMock()
    cache = AsyncMock()

    async def fetch(key, fetch_fn, **kwargs):
        return await fetch_fn()

    cache.get_or_fetch.side_effect = fetch
    monkeypatch.setattr(tier_2, "get_client", lambda: client)
    monkeypatch.setattr(tier_2, "get_cache", lambda: cache)
    # STORY-MCP-007/C-04: payload é sempre OBJETO (a forma-lista foi removida —
    # perdia a UF e devolvia custo null sem aviso).
    payload = {"itens": [{"ambiente": "Sala", "area_real_m2": "10.25", "fator_ponderacao": "0.50"}]}
    await tier_2.cub_calc_area(payload=payload, ctx=context_with_key("fixture-key"))
    client.post.assert_awaited_once_with("/v1/calc/area", json=payload, api_key="fixture-key")
    first = cache.get_or_fetch.call_args.args[0]
    await tier_2.cub_calc_area(payload=payload, ctx=context_with_key("other-key"))
    assert first != cache.get_or_fetch.call_args.args[0]
    assert "fixture-key" not in first


@pytest.mark.asyncio
async def test_calc_area_rejeita_forma_lista(monkeypatch):
    """C-04: a lista solta não é mais aceita (perdia a UF)."""
    import pydantic

    monkeypatch.setattr(tier_2, "get_client", lambda: AsyncMock())
    with pytest.raises(pydantic.ValidationError):
        await tier_2.cub_calc_area(
            payload=[{"ambiente": "Sala", "area_real_m2": "10.25"}],
            ctx=context_with_key("fixture-key"),
        )


@pytest.mark.asyncio
async def test_calc_area_posts_exact_body(monkeypatch):
    client = AsyncMock()
    response = {
        "area_real_total_m2": "100.00",
        "area_equivalente_total_m2": "100.00",
        "fator_equivalente_medio": "1.00",
        "itens": [],
        "nota_normativa": "ABNT NBR 12.721:2006",
    }
    client.post.return_value = response
    monkeypatch.setattr(tier_2, "get_client", lambda: client)
    payload = {"itens": [{"ambiente": "Apartamento", "area_real_m2": "100.00"}]}
    result = await tier_2.cub_calc_area(payload=payload, ctx=context_with_key("fixture-key"))
    # STORY-MCP-007: o cálculo vem intacto + `vigencia` (o agente precisa saber
    # se o CUB aplicado é o vigente).
    assert {k: v for k, v in result.items() if k != "vigencia"} == response
    assert "vigencia" in result
    client.post.assert_awaited_once_with("/v1/calc/area", json=payload, api_key="fixture-key")
