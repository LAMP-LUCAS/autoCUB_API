import json
from unittest.mock import AsyncMock, patch

import httpx
from starlette.routing import Match

from autocub_mcp.server import create_http_app, create_server, main


async def test_registration():
    server = create_server()
    tools = await server.list_tools()
    names = {tool.name for tool in tools}
    assert names == {
        "cub_get_uf",
        "cub_latest",
        "cub_panorama",
        "cub_dash",
        "cub_impacto_desoneracao",
        "cub_deson",
        "cub_ranking",
        "cub_historico",
        "cub_comparativo",
        "cub_padroes_list",
        "cub_sinduscons_list",
        "cub_health",
        "cub_calc_area",
    }
    assert len(tools) == 13
    for tool in tools:
        assert "api_key" not in tool.inputSchema.get("properties", {})
        assert "ctx" not in tool.inputSchema.get("properties", {})
    assert server.settings.port == 8080


def test_all_tools_have_one_liner_descriptions():
    """§2.2 (auditoria MCP de custo): guard — nenhuma tool com descrição vazia.

    A auditoria encontrou o AutoSINAPI com 19 descrições `""` (o campo que o
    agente lê na descoberta). Este guard impede regressão: toda tool desta
    superfície precisa de um one-liner legível (>= 10 chars úteis).
    """
    from autocub_mcp.server import TOOLS

    for function, description in TOOLS:
        assert description and description.strip(), function.__name__
        assert len(description.strip()) >= 10, function.__name__


def test_both_transports_route():
    app = create_http_app(create_server())
    for method in ("GET", "POST", "DELETE"):
        scope = {"type": "http", "path": "/sse", "root_path": "", "method": method}
        assert any(route.matches(scope)[0] == Match.FULL for route in app.routes)
    assert any(route.path == "/messages" for route in app.routes)


def test_deprecated_aliases_warn_and_canonical_survivors():
    """§5.8 (auditoria MCP de custo): aliases deprecados avisam na descrição
    por 1 release; as canônicas sobrevivem sem aviso e sem o rótulo legado."""
    from autocub_mcp.server import TOOLS

    descs = {fn.__name__: desc for fn, desc in TOOLS}

    # deprecadas — apontam a sobrevivente (RED: sem "DEPRECATED" hoje)
    assert "DEPRECATED" in descs["cub_dash"]
    assert "cub_panorama" in descs["cub_dash"]
    assert "DEPRECATED" in descs["cub_impacto_desoneracao"]
    assert "cub_deson" in descs["cub_impacto_desoneracao"]

    # canônicas — sem aviso e sem o rótulo "alias REST legado" (RED: há)
    for canonica in ("cub_panorama", "cub_deson"):
        assert "DEPRECATED" not in descs[canonica]
        assert "alias REST legado" not in descs[canonica]


async def test_streamable_handshake_and_discovery():
    server = create_server()
    app = create_http_app(server)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client,
    ):
        headers = {"Accept": "application/json, text/event-stream"}
        response = await client.post(
            "/sse",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "unit-test", "version": "1"},
                },
            },
        )
        assert response.status_code == 200
        headers["Mcp-Session-Id"] = response.headers["mcp-session-id"]
        headers["MCP-Protocol-Version"] = "2025-03-26"
        response = await client.post(
            "/sse", headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        assert response.status_code == 202
        response = await client.post(
            "/sse", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        data = next(line[6:] for line in response.text.splitlines() if line.startswith("data: "))
        assert len(json.loads(data)["result"]["tools"]) == 13
        assert (await client.get("/health")).json()["status"] == "ok"


async def test_lifespan_closes_resources():
    from autocub_mcp.server import lifespan

    with patch("autocub_mcp.server.tier_1.close_resources", new_callable=AsyncMock) as close:
        async with lifespan(create_server()):
            close.assert_not_awaited()
        close.assert_awaited_once()


def test_main_http():
    with patch("autocub_mcp.server.uvicorn.run") as run:
        main()
    assert run.call_args.kwargs["port"] == 8080


def test_main_stdio(monkeypatch):
    monkeypatch.setenv("AUTOCUB_MCP_TRANSPORT", "stdio")
    with patch("autocub_mcp.server.create_server") as create:
        main()
    create.return_value.run.assert_called_once_with(transport="stdio")
