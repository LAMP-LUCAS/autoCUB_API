import logging
import sys
from contextlib import asynccontextmanager

import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from autocub_mcp.config import get_config
from autocub_mcp.resources import register_resources
from autocub_mcp.tools import tier_1, tier_2

TOOLS = (
    (tier_1.cub_get_uf, "Consulta CUB por UF, período, regime e sindicato."),
    (tier_1.cub_latest, "Últimas cotações CUB com fonte e referência."),
    (tier_1.cub_panorama, "Panorama CUB por UF: métricas consolidadas, tipologias e árvore NBR (canônica)."),
    (tier_1.cub_dash, "DEPRECATED (remoção no próximo release): use cub_panorama — mesmo dado e endpoint."),
    (tier_1.cub_impacto_desoneracao, "DEPRECATED (remoção no próximo release): use cub_deson — mesmo dado e endpoint."),
    (tier_1.cub_deson, "Impacto da desoneração da folha (CPRB) por UF: economia R$/m² e % (canônica)."),
    (tier_1.cub_ranking, "Ranking CUB por projeto-padrão e período."),
    (tier_1.cub_historico, "Série histórica CUB por UF e projeto-padrão."),
    (tier_1.cub_comparativo, "Comparativo CUB entre UFs separadas por vírgula."),
    (tier_1.cub_padroes_list, "Catálogo de projetos-padrão NBR 12.721."),
    (tier_1.cub_sinduscons_list, "Catálogo de sindicatos por UF e região."),
    (tier_1.cub_health, "Saúde da API CUB via gateway."),
    (
        tier_2.cub_calc_area,
        "Calcula área equivalente em m² (NBR 12.721) e custo estimativo via REST, "
        "sem persistência. **Tipagem (ADR 009):** todo valor numérico da resposta é "
        "JSON number (float), nunca string; datas são string ISO. Sem CUB para a UF, "
        "a resposta traz `erro` + `motivo` + `ufs_com_cub_mais_proximas`.",
    ),
)


def setup_logging() -> None:
    structlog.configure(
        processors=[structlog.stdlib.add_log_level, structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    logging.basicConfig(stream=sys.stderr, level=get_config().log_level, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(server: FastMCP):
    try:
        yield {}
    finally:
        await tier_1.close_resources()


def create_server() -> FastMCP:
    config = get_config()
    server = FastMCP(
        "AutoCUB",
        host=config.mcp_host,
        port=config.mcp_port,
        log_level=config.log_level,
        lifespan=lifespan,
    )
    for function, description in TOOLS:
        server.tool(name=function.__name__, description=description)(function)
    register_resources(server)
    return server


async def health(request):
    return JSONResponse({"status": "ok", "service": "autocub-mcp"})


def create_http_app(server: FastMCP) -> Starlette:
    server.settings.streamable_http_path = "/sse"
    sse_routes = list(server.sse_app().routes)
    app = server.streamable_http_app()
    for route in reversed(sse_routes):
        app.routes.insert(0, route)
    app.routes.append(Route("/health", health, methods=["GET"]))
    return app


def main() -> None:
    setup_logging()
    config = get_config()
    server = create_server()
    if config.mcp_transport == "streamable-http":
        uvicorn.run(
            create_http_app(server),
            host=config.mcp_host,
            port=config.mcp_port,
            log_level=config.log_level.lower(),
        )
    else:
        server.run(transport=config.mcp_transport)


if __name__ == "__main__":
    main()
