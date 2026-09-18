from unittest.mock import AsyncMock

import pytest

from autocub_mcp.tools import tier_1

CASES = [
    (
        "cub_get_uf",
        {"uf": "go", "ano": 2026, "mes": 8, "sinduscon_id": 2},
        "/v1/cub/GO",
        {"ano": 2026, "mes": 8, "desoneracao": "SEM_DESONERACAO", "sinduscon_id": 2},
    ),
    ("cub_latest", {}, "/v1/cub/latest", {"desoneracao": "SEM_DESONERACAO"}),
    ("cub_panorama", {"uf": "GO"}, "/v1/cub/GO/panorama", {"desoneracao": "SEM_DESONERACAO"}),
    ("cub_dash", {"uf": "GO"}, "/v1/cub/GO/dash", {"desoneracao": "SEM_DESONERACAO"}),
    ("cub_impacto_desoneracao", {"uf": "GO"}, "/v1/cub/GO/impacto-desoneracao", {}),
    ("cub_deson", {"uf": "GO"}, "/v1/cub/GO/deson", {}),
    (
        "cub_ranking",
        {},
        "/v1/cub/ranking",
        {"codigo_padrao": "R1-N", "desoneracao": "SEM_DESONERACAO"},
    ),
    (
        "cub_historico",
        {"uf": "GO", "codigo_padrao": "r8-n", "ano_inicio": 2024},
        "/v1/cub/GO/historico/R8-N",
        {"ano_inicio": 2024, "desoneracao": "SEM_DESONERACAO"},
    ),
    (
        "cub_comparativo",
        {"ufs": "GO,MG"},
        "/v1/cub/comparativo",
        {"ufs": "GO,MG", "codigo_padrao": "R1-N", "desoneracao": "SEM_DESONERACAO"},
    ),
    ("cub_padroes_list", {"categoria": "RESIDENCIAL"}, "/v1/padroes", {"categoria": "RESIDENCIAL"}),
    ("cub_sinduscons_list", {"ativo_apenas": False}, "/v1/sinduscons", {"ativo_apenas": False}),
    ("cub_health", {}, "/v1/health", {}),
]


@pytest.mark.parametrize("name,arguments,path,params", CASES)
async def test_route_and_auth_partition(monkeypatch, name, arguments, path, params):
    client = AsyncMock()
    client.get.return_value = {"value": "1.2300", "source": "CBIC"}
    cache = AsyncMock()

    async def fetch(key, fetch_fn, **kwargs):
        assert key.startswith("autocub:")
        assert "fixture-key" not in key
        return await fetch_fn()

    cache.get_or_fetch.side_effect = fetch
    monkeypatch.setattr(tier_1, "get_client", lambda: client)
    monkeypatch.setattr(tier_1, "get_cache", lambda: cache)
    tool = getattr(tier_1, name)
    result = await tool(**arguments, api_key="fixture-key")
    assert result == client.get.return_value
    client.get.assert_awaited_once_with(path, params=params or None, api_key="fixture-key")
    first_key = cache.get_or_fetch.call_args.args[0]
    await tool(**arguments, api_key="another-key")
    assert cache.get_or_fetch.call_args.args[0] != first_key
