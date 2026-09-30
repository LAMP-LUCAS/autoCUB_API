"""Contrato único do AutoCUB — STORY-MCP-007 (Onda A: §4 do relatório + B-03).

Antes desta onda, "sem dado" tinha 4 formatos: cinco tools devolviam **texto
puro** com `isError=true` (o agente recebia "falha" para um dado que não existe
— e framework trata `isError` como retry), `cub_get_uf` devolvia objeto solto e
`cub_sinduscons_list` devolvia envelope.

Agora: um envelope só, com `status`, `disponivel`, `consulta`, `motivo`
(código + descrição + natureza), `vigencia`, `alternativas`, `orientacao` e
`itens: []` — nunca `content: []`, nunca erro genérico. Resposta **com dado**
ganha `vigencia` (vigente + meses de atraso), porque AC responder 2026-03 sem
avisar é erro de orçamento.

Equivalentes vivos: claims §C-10 (envelope) e §C-11 (vigência) do gate da casa.
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.server.fastmcp import Context

from autocub_mcp import envelope
from autocub_mcp.tools import tier_1, tier_2

SNAPSHOT = {
    "uf": "RJ", "codigo_padrao": "R1-N", "desoneracao": "SEM_DESONERACAO",
    "data_referencia": "2026-08-01", "valor_m2": Decimal("2984.18"),
    "categoria": "RESIDENCIAL", "uf_cobertura": "RJ",
}


def context_with_key(key: str = "fixture-key"):
    request = SimpleNamespace(headers={"x-api-key": key})
    return Context(request_context=SimpleNamespace(request=request))


def _patch(monkeypatch, client, *, uf="RJ", ref="2026-08", extra_ufs=("GO",), resultado=None):
    """Fixa o snapshot de cobertura e o client HTTP das tools.

    `resultado` sobrescreve a resposta do GET (ex.: `[]` para "sem dado").
    O snapshot espelha o que `envelope.snapshot()` produz de verdade: chaves
    ordenadas.
    """
    registros = [
        {"uf": uf, "data_referencia": f"{ref}-01", "codigo_padrao": "R1-N",
         "sinduscon_id": 1, "valor_m2": Decimal("2984.18")},
    ] + [
        {"uf": u, "data_referencia": f"{ref}-01", "codigo_padrao": "R1-N",
         "sinduscon_id": 2, "valor_m2": Decimal("2400.00")} for u in extra_ufs
    ]
    envelope.limpar_cache_snapshot()

    async def fake_snapshot(ctx):
        return {
            "ufs": {u: ref for u in ("RJ", "GO")},
            "por_referencia": {ref: ["GO", "RJ"]},
            "padroes_por_uf": {"RJ": {"R1-N"}, "GO": {"R1-N"}},
            "referencia_mais_recente": ref,
            "ufs_com_dado": ["GO", "RJ"],
        }

    monkeypatch.setattr(envelope, "snapshot", fake_snapshot)

    cache = AsyncMock()

    async def fetch(key, fetch_fn, **kwargs):
        return await fetch_fn()

    cache.get_or_fetch.side_effect = fetch
    client.get.return_value = registros if resultado is None else resultado
    monkeypatch.setattr(tier_1, "get_client", lambda: client)
    monkeypatch.setattr(tier_1, "get_cache", lambda: cache)
    monkeypatch.setattr(tier_2, "get_client", lambda: client)
    monkeypatch.setattr(tier_2, "get_cache", lambda: cache)
    return client


class TestVigencia:
    def test_meses_de_atraso(self):
        assert envelope.meses_de_atraso("2026-03-01", "2026-08-01") == 5
        assert envelope.meses_de_atraso("2026-08-01", "2026-08-01") == 0
        assert envelope.meses_de_atraso("2026-09-01", "2026-08-01") == 0  # nunca negativo

    def test_vigente_quando_e_a_mais_recente(self):
        v = envelope.vigencia("2026-08-01", "2026-08-01")
        assert v["vigente"] is True
        assert v["meses_de_atraso"] == 0
        assert "alerta" not in v

    def test_defasada_traz_alerta(self):
        v = envelope.vigencia("2026-03-01", "2026-08-01")
        assert v["vigente"] is False
        assert v["meses_de_atraso"] == 5
        assert "5 mês(es)" in v["alerta"]
        assert v["ultima_publicacao_conhecida"] == "2026-08"

    def test_normaliza_date_e_string(self):
        from datetime import date

        assert envelope.vigencia(date(2026, 3, 1), "2026-08-01")["meses_de_atraso"] == 5
        assert envelope.vigencia("2026-03", "2026-08")["meses_de_atraso"] == 5


class TestCatalogo:
    def test_todo_motivo_tem_descricao_e_natureza(self):
        for codigo, (descricao, natureza) in envelope.CATALOGO_MOTIVOS.items():
            assert descricao and natureza in (
                "limitacao_externa", "ingestao_pendente", "defasagem", "parametro_invalido",
            ), codigo

    def test_motivo_tem_espelho_textual(self):
        m = envelope.motivo("CUB_NAO_PUBLICADO_POR_UF")
        assert m["codigo"] == "CUB_NAO_PUBLICADO_POR_UF"
        assert m["texto"] == m["descricao"]      # espelho para leitura legada

    def test_orientacao_para_cada_motivo(self):
        for codigo in envelope.CATALOGO_MOTIVOS:
            o = envelope._orientacao(codigo)
            assert o["acao_recomendada"] and o["texto"] and o["risco"]


class TestSemDado:
    @pytest.mark.asyncio
    async def test_uf_sem_adapter_vira_envelope(self, monkeypatch):
        from autocub_mcp.client import NotFoundError

        client = AsyncMock()
        client.get.side_effect = NotFoundError("CUB não encontrado. LIM-38 [cid=abc]")
        _patch(monkeypatch, client, uf="RJ")

        out = await tier_1.cub_get_uf("SP", ctx=context_with_key())
        assert out["status"] == "sem_dado"
        assert out["disponivel"] is False
        assert out["motivo"]["codigo"] == "CUB_NAO_PUBLICADO_POR_UF"
        assert out["consulta"]["uf"] == "SP"
        assert out["itens"] == [] and out["total"] == 0
        assert out["alternativas"]["ufs_com_dado"] == ["GO", "RJ"]
        assert out["orientacao"]["acao_recomendada"] == "usar_uf_proxima"
        # regra inviolável: sem dado não vem com número
        assert "valor_m2" not in str(out)

    @pytest.mark.asyncio
    async def test_404_comum_vira_sindicado_nao_cadastrado(self, monkeypatch):
        from autocub_mcp.client import NotFoundError

        client = AsyncMock()
        client.get.side_effect = NotFoundError("CUB não encontrado. [cid=abc]")
        _patch(monkeypatch, client)

        out = await tier_1.cub_historico("ZZ", "R1-N", ctx=context_with_key())
        assert out["motivo"]["codigo"] == "SEM_SINDUSCON_CADASTRADO"
        assert out["motivo"]["natureza"] == "limitacao_externa"

    @pytest.mark.asyncio
    async def test_periodo_sem_cotacao(self, monkeypatch):
        client = AsyncMock()
        _patch(monkeypatch, client, resultado=[])

        out = await tier_1.cub_get_uf("RJ", ano=2026, mes=7, ctx=context_with_key())
        assert out["motivo"]["codigo"] == "SEM_COTACAO_PARA_O_PERIODO"
        assert out["motivo"]["natureza"] == "ingestao_pendente"
        # a UF tem dado, então a vigência da UF é aproveitada
        assert out["vigencia"]["data_referencia"] == "2026-08"

    @pytest.mark.asyncio
    async def test_uf_que_nao_existe_no_acervo(self, monkeypatch):
        client = AsyncMock()
        _patch(monkeypatch, client, resultado=[])

        out = await tier_1.cub_dash("XX", ctx=context_with_key())
        assert out["motivo"]["codigo"] == "CUB_NAO_PUBLICADO_POR_UF"

    @pytest.mark.asyncio
    async def test_calc_area_sem_cub_preserva_campos_do_c04(self, monkeypatch):
        """O envelope entra COMPLEMENTANDO o que o claim C-04 exige."""
        client = AsyncMock()
        client.post.return_value = {
            "area_real_total_m2": 50.0,
            "custo_estimado_total": None,
            "cub_m2_aplicado": None,
            "erro": "CUB_INDISPONIVEL_PARA_UF",
            "motivo": "A UF SP não possui sindicato com CUB cadastrado",
            "ufs_com_cub_mais_proximas": ["RJ", "MG"],
            "itens": [],
        }
        _patch(monkeypatch, client)

        out = await tier_2.cub_calc_area(
            payload={"uf": "SP", "itens": [{"ambiente": "Sala", "area_real_m2": 50.0}]},
            ctx=context_with_key(),
        )
        assert out["status"] == "sem_dado"
        assert out["disponivel"] is False
        assert out["consulta"]["uf"] == "SP"
        assert out["ufs_com_cub_mais_proximas"] == ["RJ", "MG"]


class TestComDado:
    @pytest.mark.asyncio
    async def test_lista_plana_preservada_com_vigencia_por_item(self, monkeypatch):
        client = AsyncMock()
        _patch(monkeypatch, client, ref="2026-03", extra_ufs=("GO",))

        out = await tier_1.cub_latest(uf="RJ", ctx=context_with_key())
        assert isinstance(out, list), "UF coberta continua lista plana (LIM-38)"
        assert out[0]["vigencia"]["vigente"] is True
        assert out[0]["vigencia"]["meses_de_atraso"] == 0

    @pytest.mark.asyncio
    async def test_item_defasado_marca_vigencia(self, monkeypatch):
        client = AsyncMock()
        _patch(monkeypatch, client, uf="AC", ref="2026-03", extra_ufs=("RJ",))

        async def fake_snapshot(ctx):
            return {
                "ufs": {"AC": "2026-03", "RJ": "2026-08"},
                "por_referencia": {"2026-03": ["AC"], "2026-08": ["RJ"]},
                "padroes_por_uf": {"AC": {"R1-N"}, "RJ": {"R1-N"}},
                "referencia_mais_recente": "2026-08",
                "ufs_com_dado": ["AC", "RJ"],
            }

        monkeypatch.setattr(envelope, "snapshot", fake_snapshot)
        out = await tier_1.cub_get_uf("AC", ctx=context_with_key())
        item = out[0]
        assert item["vigencia"]["vigente"] is False
        assert item["vigencia"]["meses_de_atraso"] == 5
        assert "5 mês(es)" in item["vigencia"]["alerta"]

    @pytest.mark.asyncio
    async def test_dicionario_recebe_vigencia_no_topo(self, monkeypatch):
        client = AsyncMock()
        _patch(monkeypatch, client,
               resultado={"uf": "RJ", "data_referencia": "2026-08-01", "cotacoes": []})

        out = await tier_1.cub_dash("RJ", ctx=context_with_key())
        assert out["vigencia"]["vigente"] is True
        assert out["vigencia"]["escopo"] == "uf"

    @pytest.mark.asyncio
    async def test_catalogo_perene_sem_vigencia_mensal(self, monkeypatch):
        client = AsyncMock()
        _patch(monkeypatch, client, resultado={"items": [{"codigo": "R1-N"}]})

        out = await tier_1.cub_padroes_list(ctx=context_with_key())
        assert out["vigencia"]["escopo"] == "catalogo_perene"
        assert out["vigencia"]["meses_de_atraso"] == 0

    @pytest.mark.asyncio
    async def test_calc_area_com_cub_recebe_vigencia(self, monkeypatch):
        client = AsyncMock()
        client.post.return_value = {
            "area_real_total_m2": 50.0, "custo_estimado_total": 86779.95,
            "cub_m2_aplicado": 1735.6, "erro": None, "itens": [],
        }
        _patch(monkeypatch, client)

        out = await tier_2.cub_calc_area(
            payload={"uf": "RJ", "itens": [{"ambiente": "Sala", "area_real_m2": 50.0}]},
            ctx=context_with_key(),
        )
        assert out["vigencia"]["vigente"] is True
        assert "status" not in out, "com dado não recebe status de sem_dado"
