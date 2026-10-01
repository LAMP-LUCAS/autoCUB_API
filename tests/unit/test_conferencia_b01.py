"""STORY-MCP-007 · conferência da fonte na ingestão (proteção real).

O alarme de "provisório" foi removido porque a hipótese que o sustentava
(forward-fill nosso) foi refutada: baixando os PDFs do cub.org.br, o
Sinduscon-AM PUBLICA o mesmo índice em maio e junho. O valor é o oficial.

A proteção que substitui o alarme é **verificar**, não suspeitar: antes de
gravar, comparar o que a fonte DECLARA com o que foi pedido e com o que foi
gravado. Só há sinal quando há fato.

Cada conferência é **tri-estado** — a lição do P0-1 é que "não sei" nunca pode
ser reportado como "está ruim":

* ``confere``       — a fonte declara a competência pedida;
* ``divergente``    — a fonte declara OUTRA competência → arquivo errado (fato);
* ``indeterminado`` — o PDF não expõe o período de forma legível → grava e
  registra que não deu para conferir (nunca bloqueia por ignorância).

O texto real dos PDFs do CBIC (medido em 2026-10-01) vem em dois formatos:

* ``(NBR 12.721:2006 - CUB 2006) - Junho/2026``                    (AM, RJ, GO…)
* ``CUB/m² dados de Dezembro/2025, para ser usado em Janeiro/2026`` (RR, …)

No segundo formato a competência é a de **uso**, não a de "dados de" — comparar
com a errada marcaria divergência em todos os arquivos de RR.
"""
from datetime import date
from decimal import Decimal

import pytest

from autocub.processor import conferencia

# ── formatos reais medidos no CBIC ──────────────────────────────────────────
TEXTO_PUBLICACAO = """\
CUB/m²
Custos Unitários Básicos de Construção
(NBR 12.721:2006 - CUB 2006) - Junho/2026
Os valores abaixo referem-se aos Custos Unitários Básicos de Construção (CUB/m²)
"""

TEXTO_USO = """\
CUB/m²
Custos Unitários Básicos de Construção
(NBR 12.721:2006 - CUB 2006)
M.Obra com Encargos Sociais Desonerados
CUB/m² dados de Dezembro/2025, para ser usado em Janeiro/2026
Com variação percentual
"""

TEXTO_SEM_ROTULO = """\
CUB/m²
dados consolidados do exercício
"""


def _competencia(texto: str, pedido: tuple[int, int]) -> dict:
    return conferencia.conferir_periodo(texto, ano=pedido[0], mes=pedido[1])


class TestConferenciaDePeriodo:
    def test_formato_de_publicacao_confere(self):
        r = _competencia(TEXTO_PUBLICACAO, (2026, 6))
        assert r["resultado"] == "confere"
        assert r["declarado"] == {"ano": 2026, "mes": 6}
        assert r["fonte"] == "publicacao"

    def test_formato_de_uso_confere_ignora_a_data_de_dados(self):
        """RR: 'dados de Dezembro/2025, para ser usado em Janeiro/2026'.
        A competência é a de USO — comparar com 'dados de' marcaria tudo."""
        r = _competencia(TEXTO_USO, (2026, 1))
        assert r["resultado"] == "confere"
        assert r["declarado"] == {"ano": 2026, "mes": 1}
        assert r["fonte"] == "uso"

    def test_arquivo_errado_e_divergente(self):
        """Pediu junho, o arquivo se declara março de 2023 — FATO, não hipótese."""
        texto = TEXTO_PUBLICACAO.replace("Junho/2026", "Março/2023")
        r = _competencia(texto, (2026, 6))
        assert r["resultado"] == "divergente"
        assert r["declarado"] == {"ano": 2023, "mes": 3}

    def test_sem_rotulo_e_indeterminado(self):
        """Não saber não é divergência — é indeterminado (nunca bloqueia)."""
        r = _competencia(TEXTO_SEM_ROTULO, (2026, 6))
        assert r["resultado"] == "indeterminado"
        assert r["declarado"] is None

    def test_texto_vazio_e_indeterminado(self):
        assert _competencia("", (2026, 6))["resultado"] == "indeterminado"

    def test_acentos_e_caixa(self):
        texto = TEXTO_PUBLICACAO.replace("Junho/2026", "MARÇO/2026")
        r = _competencia(texto, (2026, 3))
        assert r["resultado"] == "confere"

    def test_ano_completo(self):
        r = _competencia(TEXTO_PUBLICACAO.replace("Junho/2026", "Junho/26"), (2026, 6))
        assert r["resultado"] in ("confere", "indeterminado")


class TestFidelidadeDaGravacao:
    """C2: depois de gravar, relemos as linhas escritas e comparamos com o que
    o PDF disse. É o único check que pega erro de CHAVE — valor gravado na UF,
    competencia ou desoneracao errada, que nenhum outro check enxerga."""

    def _registro(self, **kw):
        base = {
            "uf": "AM", "codigo_padrao": "R1-N", "desoneracao": "SEM_DESONERACAO",
            "data_referencia": date(2026, 6, 1), "valor_m2": Decimal("3897.23"),
        }
        base.update(kw)
        return base

    def test_confere_quando_banco_iguala_pdf(self):
        r = conferencia.conferir_gravacao(
            [self._registro()], {("R1-N", "SEM_DESONERACAO"): Decimal("3897.23")}
        )
        assert r["resultado"] == "confere"
        assert r["conferidos"] == 1 and r["divergentes"] == 0

    def test_divergente_quando_valor_diferente(self):
        r = conferencia.conferir_gravacao(
            [self._registro()], {("R1-N", "SEM_DESONERACAO"): Decimal("9999.99")}
        )
        assert r["resultado"] == "divergente"
        assert r["divergentes"] == 1
        assert r["divergencias"][0]["codigo_padrao"] == "R1-N"

    def test_ignora_registro_em_quarentena(self):
        """O que foi para quarentena não está no banco — não é divergência."""
        r = conferencia.conferir_gravacao([], {})
        assert r["resultado"] == "confere"
        assert r["conferidos"] == 0

    def test_comparacao_tolerante_a_centavos(self):
        """Decimal vs float: diferença de 1e-9 não é divergência."""
        r = conferencia.conferir_gravacao(
            [self._registro(valor_m2=Decimal("3897.23"))],
            {("R1-N", "SEM_DESONERACAO"): Decimal("3897.2300000001")},
        )
        assert r["resultado"] == "confere"

    def test_varios_itens_contabiliza(self):
        # o mesmo PDF pode legitimately trazer o mesmo valor para vários padrões
        registros = [
            self._registro(codigo_padrao="R1-N"),
            self._registro(codigo_padrao="R8-N"),
            self._registro(codigo_padrao="CAL-8-A"),
        ]
        banco = {
            ("R1-N", "SEM_DESONERACAO"): Decimal("3897.23"),
            ("R8-N", "SEM_DESONERACAO"): Decimal("3897.23"),
            ("CAL-8-A", "SEM_DESONERACAO"): Decimal("3897.23"),
        }
        r = conferencia.conferir_gravacao(registros, banco)
        assert r["conferidos"] == 3 and r["divergentes"] == 0


class TestGuardaDeGravacao:
    """Regra: arquivo com período DIVERGENTE não é gravado. Um mês ausente é
    melhor que um mês com o valor de outro — e o alerta tem FATO."""

    def test_divergente_bloqueia(self):
        decisao = conferencia.decidir({"resultado": "divergente", "declarado": {"ano": 2023, "mes": 3}})
        assert decisao["gravar"] is False
        assert decisao["status"] == "CONFERIU_DIVERGENTE"

    def test_confere_grava(self):
        decisao = conferencia.decidir({"resultado": "confere", "declarado": {"ano": 2026, "mes": 6}})
        assert decisao["gravar"] is True
        assert decisao["status"] == "SUCESSO"

    def test_indeterminado_grava_mas_registra(self):
        """Nunca bloqueia por ignorancia — e deixa isso registrado."""
        decisao = conferencia.decidir({"resultado": "indeterminado", "declarado": None})
        assert decisao["gravar"] is True
        assert decisao["conferivel"] is False

    def test_status_cabe_em_varchar20(self):
        """etl_execucoes.status é varchar(20) — o status não pode estourar."""
        for resultado in ("confere", "divergente", "indeterminado"):
            assert len(conferencia.decidir({"resultado": resultado})["status"]) <= 20


class TestMensagemDeConferencia:
    """O que vai para `etl_execucoes.mensagem_erro` — precisa caber e ser curto."""

    def _msg(self, periodo, gravacao, estaveis=(), quarentenados=()):
        from autocub.tasks.etl_tasks import _montar_mensagem_conferencia
        return _montar_mensagem_conferencia(
            periodo=periodo, gravacao=gravacao,
            estaveis=list(estaveis), quarentenados=list(quarentenados),
        )

    def test_resumo_tudo_ok(self):
        msg = self._msg(
            {"resultado": "confere"}, {"resultado": "confere", "conferidos": 19},
        )
        assert "periodo conferido" in msg and "19 linhas" in msg
        assert "DIVERGENTE" not in msg

    def test_resumo_com_gravacao_divergente(self):
        msg = self._msg(
            {"resultado": "confere"},
            {"resultado": "divergente", "conferidos": 19, "divergentes": 3},
        )
        assert "GRAVACAO DIVERGENTE" in msg and "3/19" in msg

    def test_resumo_indeterminado_nao_fala_bem(self):
        msg = self._msg(
            {"resultado": "indeterminado"}, {"resultado": "confere", "conferidos": 19},
        )
        assert "nao conferivel" in msg and "DIVERGENTE" not in msg

    def test_mensagem_curta(self):
        msg = self._msg(
            {"resultado": "confere"},
            {"resultado": "confere", "conferidos": 19},
            estaveis=[1, 2], quarentenados=[1],
        )
        assert len(msg) <= 500
