"""STORY-MCP-007/B-01 — detector de índice MANTIDO entre competências.

**Correção de 2026-10-01 (medição contra a fonte):** a repetição de valor em AM
(maio = junho = 3.897,23) NÃO é defeito de carga. Baixando os PDFs direto do
cub.org.br, a fonte oficial publica **3897,23 em maio e em junho** — o
Sinduscon-AM manteve o índice. O detector existia para pegar *forward-fill
nosso*; hipótese refutada.

Consequência de projeto: deixou de marcar `dados_provisorios` e saiu da resposta
das tools. Marca só o **fato** (`INDICE_MANTIDO_ENTRE_COMPETENCIAS`) para o
operador, em `cub_health` e no log da ETL — sem veredito de desconfiança, porque
o valor é o oficial.

Continua relevante: variação 0,00% **passa** pela guarda de sanidade
(|var| > 5%), então este é o único detector que enxerga o caso.
"""
from datetime import date
from decimal import Decimal

from autocub.processor import repeticao


def _serie(valores, padrao="R1-N", uf="AM", deson="SEM_DESONERACAO", ano=2026):
    """Série mensal de uma UF/padrão, com a variação calculada como a API faz."""
    out = []
    anterior = None
    for i, valor in enumerate(valores, start=1):
        variacao = None
        if valor is not None and anterior is not None and anterior != 0:
            variacao = round((Decimal(str(valor)) / Decimal(str(anterior)) - 1) * 100, 2)
        out.append({
            "uf": uf, "codigo_padrao": padrao, "desoneracao": deson,
            "data_referencia": date(ano, i, 1),
            "valor_m2": None if valor is None else Decimal(str(valor)),
            "variacao_mensal_pct": variacao,
        })
        anterior = valor
    return out


# Valores reais lidos de cub_mensal em 2026-09-30 (AM · R1-N · SEM_DESONERACAO)
AM_REAL = [3802.44, 3781.40, 3837.16, 3897.23, 3897.23, 3897.23, 3685.04]


class TestSerieRealDeAM:
    def test_detecta_as_duas_repeticoes(self):
        repetidos = repeticao.detectar_repeticoes(_serie(AM_REAL))
        meses = {r["data_referencia"].month for r in repetidos}
        assert meses == {5, 6}, f"esperado maio e junho, veio {meses}"

    def test_marca_como_provisorio_sem_descartar(self):
        repetidos = repeticao.detectar_repeticoes(_serie(AM_REAL))
        assert repetidos, "a série real de AM deveria ser sinalizada"
        for r in repetidos:
            # FATO, sem veredito: nenhum campo diz "provisório"/"suspeito".
            assert r["fato"] == "INDICE_MANTIDO_ENTRE_COMPETENCIAS"
            assert r["meses_mantido"] == 2
            assert "dados_provisorios" not in r and "alerta_valor_repetido" not in r
            # o valor continua lá: descartar viraria buraco
            assert r["valor_m2"] is not None

    def test_nao_marca_a_ressincronizacao_de_julho(self):
        """Julho (3.685,04) difere de junho — a queda NÃO é repetição."""
        repetidos = repeticao.detectar_repeticoes(_serie(AM_REAL))
        assert 7 not in {r["data_referencia"].month for r in repetidos}

    def test_nao_altera_o_registro_original(self):
        serie = _serie(AM_REAL)
        repeticao.detectar_repeticoes(serie)
        assert "fato" not in serie[4], "o input não pode ser mutado"


class TestSeriesSaudaveis:
    def test_serie_variando_nao_e_sinalizada(self):
        """Controle: RJ (2.979,44 → 2.983,09 → 2.984,18) não repete valor."""
        rj = _serie([2979.44, 2983.09, 2984.18, 2985.10], uf="RJ")
        assert repeticao.detectar_repeticoes(rj) == []

    def test_repeticao_isolada_nao_dispara(self, ):
        """1 mês repetido pode ser coincidência de arredondamento."""
        serie = _serie([100.00, 100.00, 102.00, 103.00], uf="GO")
        assert repeticao.detectar_repeticoes(serie) == []

    def test_repeticao_isolada_dispara_com_min_meses_1(self):
        serie = _serie([100.00, 100.00, 102.00], uf="GO")
        assert len(repeticao.detectar_repeticoes(serie, min_meses=1)) == 1

    def test_tres_meses_repetidos_um_grupo(self):
        serie = _serie([100.00, 100.00, 100.00, 100.00, 101.00], uf="GO")
        repetidos = repeticao.detectar_repeticoes(serie)
        assert len(repetidos) == 3
        assert {r["meses_mantido"] for r in repetidos} == {3}


class TestSeparacaoPorSerie:
    def test_nao_compara_ufs_ou_padroes_diferentes(self):
        a = _serie([100.00, 100.00, 100.00], uf="AM")
        b = _serie([100.00, 100.00, 100.00], uf="RJ")
        c = _serie([100.00, 100.00, 100.00], padrao="R8-N")
        juntos = a + b + c
        repetidos = repeticao.detectar_repeticoes(juntos)
        # 3 séries independentes: 2 meses marcados em cada
        assert len(repetidos) == 6
        assert {r["uf"] for r in repetidos} == {"AM", "RJ"}
        assert {r["codigo_padrao"] for r in repetidos} == {"R1-N", "R8-N"}

    def test_desoneracao_e_parte_da_chave(self):
        sem = _serie([100.00, 100.00, 100.00], deson="SEM_DESONERACAO")
        com = _serie([100.00, 100.00, 100.00], deson="COM_DESONERACAO")
        assert len(repeticao.detectar_repeticoes(sem + com)) == 4

    def test_registro_sem_valor_quebra_a_sequencia(self):
        """`valor_m2: None` (mês sem cotação) não pode gerar repetição indevida
        nem interromper a análise: o detector retoma a comparação depois dele."""
        # fecho um grupo de 2 meses repetidos DEPOIS do buraco
        serie = _serie([100.00, None, 100.00, 100.00, 100.00], uf="GO")
        repetidos = repeticao.detectar_repeticoes(serie)
        assert {r["data_referencia"].month for r in repetidos} == {4, 5}
        # e o buraco, sozinho, não gera nada
        assert repeticao.detectar_repeticoes(_serie([100.00, None, 100.00], uf="GO")) == []

    def test_contar_repetidos(self):
        assert repeticao.contar_repetidos(_serie(AM_REAL)) == 2
        assert repeticao.contar_repetidos(_serie([1.0, 2.0, 3.0])) == 0
