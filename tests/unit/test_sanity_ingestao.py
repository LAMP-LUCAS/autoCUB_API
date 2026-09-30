"""STORY-MCP-007/C-03 — guarda de sanidade na ingestão de CUB.

Medido em 2026-09-30: AM caiu 4,85%..−13,11% entre 2026-06 e 2026-07 (todas as
UFs com dado ficaram em ±4,33%) e o dado entrou sem nenhum aviso. A guarda
impede que a próxima execução repita isso em silêncio: registro com variação
mensal acima do limiar vai para **quarentena** e a execução é gravada como
`SUCESSO_QUARENTENA` (varchar(20) em etl_execucoes).

Nada aqui reprocessa dado — a guarda só atua em execuções futuras da ETL.
"""
from decimal import Decimal

from autocub.processor import sanity


class TestLimiar:
    def test_padrao_e_cinco_por_cento(self):
        assert sanity.LIMIAR_PADRAO_PCT == Decimal("5.0")
        assert sanity.limiar_padrao() == Decimal("5.0")

    def test_limiar_vem_do_setting(self, monkeypatch):
        from autocub.core.config import settings

        monkeypatch.setattr(settings, "CUB_VARIACAO_MAX_PCT", 8.0, raising=False)
        assert sanity.limiar_padrao() == Decimal("8.0")


class TestClassificar:
    def test_variacao_dentro_da_faixa_e_aceita(self):
        registros = [
            {"codigo_padrao": "R8-A", "variacao_mensal_pct": Decimal("1.20")},
            {"codigo_padrao": "CAL-8-A", "variacao_mensal_pct": Decimal("-0.46")},
        ]
        aceitos, quarentena = sanity.classificar_registros(registros)
        assert len(aceitos) == 2 and quarentena == []

    def test_am_e_negativo_de_12_por_cento_vai_para_quarentena(self):
        """O caso real: AM com −12,44% (variação economicamente implausível)."""
        registros = [{"codigo_padrao": "CAL-8-A", "variacao_mensal_pct": Decimal("-12.44")}]
        aceitos, quarentena = sanity.classificar_registros(registros)
        assert aceitos == []
        assert len(quarentena) == 1
        assert quarentena[0]["motivo_quarentena"] == "VARIACAO_MENSAL_FORA_DA_FAIXA"
        assert quarentena[0]["limiar_pct"] == "5.0"

    def test_limite_exato_e_aceito(self):
        """5,0% ainda é aceito (o limiar é exclusivo: > 5%)."""
        aceitos, quarentena = sanity.classificar_registros(
            [{"codigo_padrao": "R8-A", "variacao_mensal_pct": Decimal("5.0")}]
        )
        assert len(aceitos) == 1 and quarentena == []

    def test_sem_variacao_e_aceito(self):
        """Ausência de informação não é erro — o 1º mês de uma série vem assim."""
        aceitos, quarentena = sanity.classificar_registros(
            [{"codigo_padrao": "R8-A", "variacao_mensal_pct": None}]
        )
        assert len(aceitos) == 1 and quarentena == []

    def test_variacao_ilegivel_vai_para_quarentena(self):
        aceitos, quarentena = sanity.classificar_registros(
            [{"codigo_padrao": "R8-A", "variacao_mensal_pct": "n/a"}]
        )
        assert aceitos == []
        assert quarentena[0]["motivo_quarentena"] == "VARIACAO_ILEGIVEL"

    def test_limiar_customizado(self):
        aceitos, quarentena = sanity.classificar_registros(
            [{"codigo_padrao": "R8-A", "variacao_mensal_pct": Decimal("6.0")}],
            limiar=Decimal("10"),
        )
        assert len(aceitos) == 1 and quarentena == []


class TestRegistro:
    def test_sem_quarentena_retorna_sucesso(self):
        assert sanity.registrar_quarentena("GO", 1, 2026, 7, "SEM_DESONERACAO", []) == \
            sanity.STATUS_OK

    def test_com_quarentena_sinaliza_o_status(self, caplog):
        quarentena = [{"codigo_padrao": "CAL-8-A", "variacao_mensal_pct": Decimal("-12.44")}]
        with caplog.at_level("WARNING"):
            status = sanity.registrar_quarentena(
                "AM", 2, 2026, 7, "SEM_DESONERACAO", quarentena,
            )
        assert status == sanity.STATUS_QUARENTENA
        assert "QUARENTENA" in caplog.text
        assert "CAL-8-A" in caplog.text
