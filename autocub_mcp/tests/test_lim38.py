"""LIM-38 no MCP — sinalização de cobertura ausente (auditoria MCP §5.0).

Decisão do usuário (2026-09-30): **nota no response** — responder com a
nota ("dado ainda não disponibilizado pelo CBIC; equipe procurando
solução") em vez de erro/`[]` vazio. TDD: **sem RED** — LIM-38 não é
defeito e o claim do gate (`claim_lim38`) cobre a *sinalização*, nunca a
cobertura; os testes são escritos junto com a implementação.

Superfícies:
- `cub_get_uf` converte o 404 de cobertura (marcador `LIM-38` no `detail`
  repassado pelo client) em resposta com `nota_lim38`;
- 404 comum (sem o marcador) continua erro;
- `cub_latest` repassa o envelope `{uf, items: [], nota_lim38}` da API.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.server.fastmcp import Context

from autocub_mcp.client import NotFoundError
from autocub_mcp.lim38 import NOTA_LIM38
from autocub_mcp.tools import tier_1


def context_with_key(key: str):
    request = SimpleNamespace(headers={"x-api-key": key})
    return Context(request_context=SimpleNamespace(request=request))


def _wire(monkeypatch, *, side_effect=None, return_value=None):
    client = AsyncMock()
    if side_effect is not None:
        client.get.side_effect = side_effect
    else:
        client.get.return_value = return_value
    cache = AsyncMock()

    async def fetch(key, fetch_fn, **kwargs):
        return await fetch_fn()

    cache.get_or_fetch.side_effect = fetch
    monkeypatch.setattr(tier_1, "get_client", lambda: client)
    monkeypatch.setattr(tier_1, "get_cache", lambda: cache)
    return client


# `detail` como a API devolve para SP (base + nota LIM-38 + correlation).
DETALHE_LIM38 = (
    "Nenhum Sinduscon para SP. Dado de CUB ainda não disponibilizado pelo "
    "CBIC para esta UF (limitação de roadmap LIM-38: alguns estados não "
    "publicam o índice e adapters de outros ainda não foram implementados); "
    "a equipe de desenvolvimento está procurando solução."
)


def _assert_nota(texto: str) -> None:
    assert "CBIC" in texto, f"nota sem o emissor do dado: {texto!r}"
    assert "equipe" in texto, f"nota sem a equipe: {texto!r}"
    assert "solução" in texto, f"nota sem o encaminhamento: {texto!r}"


async def test_cub_get_uf_converte_404_lim38_em_resposta(monkeypatch):
    """responder > erro: o 404 de cobertura vira resposta com a nota."""
    _wire(monkeypatch, side_effect=NotFoundError(
        f"cub não encontrado. {DETALHE_LIM38} [correlation_id=abc]"))

    out = await tier_1.cub_get_uf("SP", ctx=context_with_key("fixture-key"))

    assert out["uf"] == "SP"
    assert out["encontrado"] is False
    _assert_nota(out["nota_lim38"])
    assert "LIM-38" in out["motivo"], "motivo perdeu o detail da API"
    assert "correlation_id=abc" in out["motivo"], (
        "rastreabilidade do404 descartada"
    )


async def test_cub_get_uf_404_comum_continua_erro(monkeypatch):
    """404 sem o marcador LIM-38 (outro tipo) segue como erro — a
    conversão não pode engolir falhas reais."""
    _wire(monkeypatch, side_effect=NotFoundError(
        "cub não encontrado. [correlation_id=abc]"))

    with pytest.raises(NotFoundError):
        await tier_1.cub_get_uf("SP", ctx=context_with_key("fixture-key"))


async def test_cub_latest_repassa_envelope_da_api(monkeypatch):
    """O envelope da API (sinalização LIM-38) passa intacto pela tool."""
    envelope = {"uf": "SP", "items": [], "nota_lim38": NOTA_LIM38}
    _wire(monkeypatch, return_value=envelope)

    out = await tier_1.cub_latest(uf="SP", ctx=context_with_key("fixture-key"))

    assert out is envelope
    _assert_nota(out["nota_lim38"])


def test_espelho_da_nota_bate_com_o_texto_da_api():
    """Guarda de sincronia do espelho (o MCP não importa a API — contexto
    de build separado): mesmas chaves do texto canônico."""
    _assert_nota(NOTA_LIM38)
    assert "LIM-38" in NOTA_LIM38
