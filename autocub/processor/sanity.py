"""
Guarda de sanidade na ingestão (STORY-MCP-007/C-03).

Medido em 2026-09-30: a série de **AM** caiu de 4,85% a **−13,11%** entre
2026-06 e 2026-07 — em TODOS os padrões e nas duas desonerações, enquanto as
outras 17 UFs com dado ficaram dentro de ±4,33%. Variação mensal de 12% em CUB
é economicamente implausível e indica erro de carga, unidade ou rebase na
origem. O dado entrou como se estivesse certo: nenhum aviso, nenhum log.

Esta guarda existe para que a próxima execução **não repita** isso em silêncio:

1. Registro com `|variacao_mensal_pct|` acima do limiar vai para **quarentena**:
   não entra em `cub_mensal`.
2. A execução do ETL é registrada como ``SUCESSO_QUARENTENA`` com a
   quantidade e uma amostra — o operador vê antes de o agente.
3. Nada é "corrigido" automaticamente: a causa (rebase, unidade trocada, fonte
   republicada) é decisão humana.

**Não reprocessa dado**: a guarda só atua em execuções futuras da ETL. Para
corrigir a série de AM é preciso decidir a causa (ver o diagnóstico no repo).
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from decimal import Decimal

logger = logging.getLogger("autocub.sanity")

# 5% é o limiar sugerido pela certificação: acima disso, a variação mensal de
# CUB precisa de explicação humana antes de virar número de orçamento.
LIMIAR_PADRAO_PCT = Decimal("5.0")

STATUS_OK = "SUCESSO"
# `etl_execucoes.status` é varchar(20) — o nome precisa caber.
# Um widen para varchar(30) exigiria migração; fica para depois.
STATUS_QUARENTENA = "SUCESSO_QUARENTENA"


def limiar_padrao() -> Decimal:
    """Limiar da guarda — `CUB_VARIACAO_MAX_PCT` sobrepõe o padrão."""
    try:
        from autocub.core.config import settings

        bruto = getattr(settings, "CUB_VARIACAO_MAX_PCT", None)
        if bruto not in (None, ""):
            return Decimal(str(bruto))
    except Exception as exc:  # noqa: BLE001 - config nunca quebra a ingestão
        logger.debug("guarda de sanidade: usando limiar padrão (%s)", exc)
    return LIMIAR_PADRAO_PCT


def classificar_registros(
    registros: Iterable[dict],
    limiar: Decimal | None = None,
) -> tuple[list[dict], list[dict]]:
    """Separa `registros` em (aceitos, quarentenados).

    Quarentena = `|variacao_mensal_pct|` acima do limiar. Registro sem
    variação (None) é **aceito** — ausência de informação não é sinal de
    erro, e o primeiro mês de uma série nova sempre vem assim.
    """
    limite = limiar if limiar is not None else limiar_padrao()
    aceitos: list[dict] = []
    quarentenados: list[dict] = []
    for registro in registros:
        variacao = registro.get("variacao_mensal_pct")
        if variacao is None:
            aceitos.append(registro)
            continue
        try:
            valor = abs(Decimal(str(variacao)))
        except Exception:  # noqa: BLE001 - texto ilegível também é anomalia
            quarentenados.append({**registro, "motivo_quarentena": "VARIACAO_ILEGIVEL"})
            continue
        if valor > limite:
            quarentenados.append({
                **registro,
                "motivo_quarentena": "VARIACAO_MENSAL_FORA_DA_FAIXA",
                "limiar_pct": str(limite),
            })
        else:
            aceitos.append(registro)
    return aceitos, quarentenados


def registrar_quarentena(
    uf: str,
    sinduscon_id: int,
    ano: int,
    mes: int,
    desoneracao: str,
    quarentenados: list[dict],
    limiar: Decimal | None = None,
) -> str:
    """Loga a quarentena e devolve o status a gravar em `etl_execucoes`."""
    if not quarentenados:
        return STATUS_OK
    limite = limiar if limiar is not None else limiar_padrao()
    amostra = ", ".join(
        f"{r.get('codigo_padrao')}={r.get('variacao_mensal_pct')}"
        for r in quarentenados[:5]
    )
    logger.warning(
        "QUARENTENA CUB %s (sinduscon=%s, %s-%02d, %s): %d registro(s) com "
        "|variação mensal| > %s%% fora de cub_mensal. Amostra: %s",
        uf, sinduscon_id, ano, mes, desoneracao, len(quarentenados), limite, amostra,
    )
    return STATUS_QUARENTENA
