"""STORY-MCP-007/C-01 — retorno vazio do AutoCUB é explícito (ADR 010).

Medido ao vivo em 2026-09-30: `cub_get_uf(AC, 2026-07)` respondia
`isError: false`, `content: []` (ZERO blocos) e
`structuredContent: {"result": []}` — o agente via um retorno **em branco**,
sem "sem dados para AC em 2026-07", e nada indicava falha.

O envelope só entra quando o resultado é VAZIO: resultado com linhas continua
sendo lista (o claim `claim_lim38` exige que UF coberta siga lista plana).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.server.fastmcp import Context

from autocub_mcp import envelope
from autocub_mcp.tools import tier_1


def context_with_key(key: str = "fixture-key"):
    request = SimpleNamespace(headers={"x-api-key": key})
    return Context(request_context=SimpleNamespace(request=request))


def _patch(monkeypatch, client):
    cache = AsyncMock()

    async def fetch(key, fetch_fn, **kwargs):
        return await fetch_fn()

    cache.get_or_fetch.side_effect = fetch
    monkeypatch.setattr(tier_1, "get_client", lambda: client)
    monkeypatch.setattr(tier_1, "get_cache", lambda: cache)
    return cache


class TestEnvelope:
    def test_e_vazio_somente_lista_vazia(self):
        assert envelope.e_vazio([]) is True
        assert envelope.e_vazio([{"uf": "AC"}]) is False
        assert envelope.e_vazio({}) is False
        assert envelope.e_vazio(None) is False

    def test_envelope_tem_marca_e_motivo(self):
        env = envelope.vazio()
        assert env["items"] == []
        assert env["sem_dados"] is True
        assert env["motivo"] == "SEM_COTACAO_PARA_O_PERIODO"
        assert env["total"] == 0

    def test_envelope_nao_inventa_none(self):
        env = envelope.vazio(uf="AC", ultima_referencia_disponivel=None)
        assert env["uf"] == "AC"
        assert "ultima_referencia_disponivel" not in env


class TestGetUf:
    @pytest.mark.asyncio
    async def test_periodo_sem_dado_devolve_envelope_com_ultima_referencia(self, monkeypatch):
        """AC pede 2026-07 e a última cotação é de 2026-03 — vigência vencida é
        informação, não erro."""
        client = AsyncMock()
        client.get.side_effect = [
            [],                                             # período pedido
            [{"uf": "AC", "data_referencia": "2026-03-01"}],  # sem período
        ]
        _patch(monkeypatch, client)
        out = await tier_1.cub_get_uf(uf="AC", ano=2026, mes=7, ctx=context_with_key())
        assert isinstance(out, dict)
        assert out["items"] == []
        assert out["sem_dados"] is True
        assert out["uf"] == "AC"
        assert out["ultima_referencia_disponivel"] == "2026-03-01"

    @pytest.mark.asyncio
    async def test_uf_com_dado_preserva_lista(self, monkeypatch):
        client = AsyncMock()
        client.get.return_value = [{"uf": "AC", "data_referencia": "2026-03-01"}]
        _patch(monkeypatch, client)
        out = await tier_1.cub_get_uf(uf="AC", ctx=context_with_key())
        assert isinstance(out, list) and out[0]["uf"] == "AC"

    @pytest.mark.asyncio
    async def test_sem_dado_sem_nenhuma_competencia(self, monkeypatch):
        """UF registrada mas nunca cotada: envelope sem data inventada."""
        client = AsyncMock()
        client.get.side_effect = [[], []]
        _patch(monkeypatch, client)
        out = await tier_1.cub_get_uf(uf="RO", ano=2026, mes=7, ctx=context_with_key())
        assert out["sem_dados"] is True
        assert "ultima_referencia_disponivel" not in out


class TestSinduscons:
    @pytest.mark.asyncio
    async def test_lista_vazia_vira_envelope(self, monkeypatch):
        client = AsyncMock()
        client.get.return_value = []
        _patch(monkeypatch, client)
        out = await tier_1.cub_sinduscons_list(uf="SP", ctx=context_with_key())
        assert isinstance(out, dict)
        assert out["sem_dados"] is True
        assert out["recurso"] == "/v1/sinduscons"

    @pytest.mark.asyncio
    async def test_lista_com_dado_segue_lista(self, monkeypatch):
        client = AsyncMock()
        client.get.return_value = [{"uf": "GO", "id": 1}]
        _patch(monkeypatch, client)
        out = await tier_1.cub_sinduscons_list(uf="GO", ctx=context_with_key())
        assert isinstance(out, list)
