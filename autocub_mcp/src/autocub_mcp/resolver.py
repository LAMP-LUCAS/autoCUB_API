import re

_PATH_PATTERNS = [
    (r"/v1/cub/[^/]+/historico/[^/]+", "Histórico CUB"),
    (r"/v1/cub/[^/]+/(?:panorama|dash)", "Panorama CUB"),
    (r"/v1/cub/[^/]+/(?:impacto-desoneracao|deson)", "Impacto da desoneração"),
    (r"/v1/cub/ranking", "Ranking CUB"),
    (r"/v1/cub/comparativo", "Comparativo CUB"),
    (r"/v1/cub/[^/]+", "Cotações CUB"),
    (r"/v1/padroes", "Padrões construtivos"),
    (r"/v1/sinduscons", "Sinduscons"),
    (r"/v1/calc/area", "Cálculo de área equivalente"),
    (r"/v1/health", "Health check"),
]


def resolve_resource(path: str) -> str:
    for pattern, name in _PATH_PATTERNS:
        if re.fullmatch(pattern, path):
            return name
    return "recurso"
