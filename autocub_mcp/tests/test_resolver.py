import pytest

from autocub_mcp.resolver import resolve_resource


@pytest.mark.parametrize(
    "path",
    ["/v1/cub/GO", "/v1/cub/GO/historico/R8-N", "/v1/cub/latest", "/v1/calc/area", "/v1/padroes"],
)
def test_known_resource(path):
    assert resolve_resource(path) != "recurso"


def test_unknown_resource():
    assert resolve_resource("/unknown") == "recurso"
