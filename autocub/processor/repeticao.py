"""Detector de valor repetido na ingestão — STORY-MCP-007/B-01.

Medido em 2026-09-30: a série de **AM** não estava corrompida — a matemática
está correta. O defeito é de **ingestão**: maio e junho repetem o valor de abril
(3.897,23) e julho ressincroniza (−5,44% de uma vez). Forward-fill ou
republicação, não movimentação econômica:

    AM · R1-N      2026-04  3.897,23   var  +1,57%
                   2026-05  3.897,23   var   0,00%   <-- repetido
                   2026-06  3.897,23   var   0,00%   <-- repetido
                   2026-07  3.685,04   var  -5,44%   <-- ressincronização

O acúmulo dessa defasagem é o que apareceu como "variação implausível". E como
o `variacao_mensal_pct` de 0,00% está dentro da faixa da guarda de sanidade
(|var| > 5%), ela **não** disparava: era preciso um detector específico.

O que este detector faz:

* ``repeticoes_por_serie`` — agrupa os registros por (UF, padrão, desoneração) e
  aponta meses com valor idêntico ao anterior (repetição é suspeita por si;
  CUB não fica parado 2 meses seguidos sem justificativa econômica);
* marca o registro com o FATO ``INDICE_MANTIDO_ENTRE_COMPETENCIAS`` e
  ``meses_mantido`` — sem veredito de desconfiança;
* **não descarta** o registro — descartar criaria buraco na série, que é pior
  que um valor repetido ASSINALADO (a USP número inventado, o buraco calado).

Nada aqui reprocessa dado. **E a série de AM não precisa**: o dry-run de
2026-10-01 provou que a base está fiel ao PDF publicado (o Sinduscon-AM
publicou 2026-06 com os valores de 2026-05) — reprocessar seria operação sem
efeito. A correção depende da fonte, não da carga (ver
`docs/DIAGNOSTICO_DADOS_AM_AC_PI.md`, seção 2c).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Iterable

logger = logging.getLogger("autocub.repeticao")

FATO = "INDICE_MANTIDO_ENTRE_COMPETENCIAS"

# Quantos meses seguidos com o MESMO valor já caracterizam forward-fill. Com
# 1 repetição isolada pode ser coincidência de arredondamento (centavos).
MIN_MESES_REPETIDOS = 2


def series_de(registros: Iterable[dict]) -> dict[tuple, list[dict]]:
    """Agrupa registros por (uf, padrão, desoneração) preservando a ordem."""
    series: dict[tuple, list[dict]] = defaultdict(list)
    for registro in registros:
        chave = (
            registro.get("uf") or registro.get("sinduscon_id"),
            registro.get("codigo_padrao"),
            registro.get("desoneracao"),
        )
        series[chave].append(registro)
    for itens in series.values():
        itens.sort(key=lambda r: (r.get("data_referencia") is None, r.get("data_referencia")))
    return series


def _meses_repetidos(itens: list[dict]) -> list[int]:
    """Índices dos itens cujo valor é igual ao do item anterior."""
    repetidos: list[int] = []
    anterior: Decimal | None = None
    for i, item in enumerate(itens):
        valor = item.get("valor_m2")
        if valor is None:
            anterior = None
            continue
        try:
            atual = Decimal(str(valor))
        except Exception:  # noqa: BLE001 - texto ilegível não é repetição
            anterior = None
            continue
        if anterior is not None and atual == anterior:
            repetidos.append(i)
        anterior = atual
    return repetidos


def detectar_repeticoes(
    registros: Iterable[dict],
    min_meses: int = MIN_MESES_REPETIDOS,
) -> list[dict]:
    """Registros com valor repetido por `min_meses` meses seguidos ou mais.

    Devolve cópias anotadas (o original não é mutado) com ``fato`` e
    ``meses_mantido`` — o FATO de que o índice foi mantido, sem veredito.
    """
    itens = list(registros)
    anotados: dict[int, dict] = {}
    for chave, serie in series_de(itens).items():
        repetidos = _meses_repetidos(serie)
        if not repetidos:
            continue
        # agrupa repetições consecutivas
        grupos: list[list[int]] = []
        for indice in repetidos:
            if grupos and indice == grupos[-1][-1] + 1:
                grupos[-1].append(indice)
            else:
                grupos.append([indice])
        for grupo in grupos:
            if len(grupo) < min_meses:
                continue
            uf, padrao, deson = chave
            for indice in grupo:
                original = serie[indice]
                copia = dict(original)
                copia["fato"] = FATO
                copia["meses_mantido"] = len(grupo)
                anotados[id(original)] = copia
                logger.info(
                    "INDICE MANTIDO %s/%s (%s): %d competência(s) com valor %s a partir de %s",
                    uf, padrao, deson, len(grupo), original.get("valor_m2"),
                    original.get("data_referencia"),
                )
    return [anotados[id(r)] for r in itens if id(r) in anotados]


def contar_repetidos(registros: Iterable[dict], **kwargs) -> int:
    return len(detectar_repeticoes(registros, **kwargs))
