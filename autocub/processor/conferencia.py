"""
Conferência da fonte na ingestão — STORY-MCP-007 (proteção real).

O alarme de "dado provisório" foi **removido** porque a hipótese que o
sustentava (forward-fill nosso) foi refutada: baixando os PDFs do cub.org.br em
2026-10-01, o Sinduscon-AM publica o mesmo índice em maio e junho. O valor é o
oficial, e desacreditá-lo tinha risco inverso ao do defeito original.

Esta é a proteção que substitui o alarme: **verificar, não suspeitar**. Antes e
depois de gravar, comparamos o que a fonte **declara** e o que foi **gravado**
com o que foi **pedido**. Só há sinal quando há fato.

Cada conferência é **tri-estada** — "não sei" nunca é reportado como "está
ruim"::

    confere         a fonte declara a competência pedida
    divergente      a fonte declara OUTRA competência  -> arquivo errado (fato)
    indeterminate  o PDF não expõe o período de forma legível -> grava e
                    registra que não deu para conferir (nunca bloqueia)

Formatos de rótulo reais do CBIC (medidos em 2026-10-01, 1.141 arquivos):

* ``(NBR 12.721:2006 - CUB 2006) - Junho/2026``                     (AM, RJ, GO…)
* ``CUB/m² dados de Dezembro/2025, para ser usado em Janeiro/2026``  (RR, …)

No segundo formato a competência é a de **USO**, não a de "dados de" — comparar
com a errada marcaria divergência em 100% dos arquivos daquele formato.
"""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Any, Iterable, Mapping, Optional

CONFERE = "confere"
DIVERGENTE = "divergente"
INDETERMINADO = "indeterminado"

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12,
}

# "para ser usado em Janeiro/2026" (ou "usado em") — competência de USO.
RE_USO = re.compile(r"usad[oa]\s+em\s+([A-Za-zÀ-ÿ]+)\s*/\s*(\d{4})", re.IGNORECASE)
# "- Junho/2026" no fim da linha — competência de PUBLICAÇÃO.
RE_PUBLICACAO = re.compile(r"-\s*([A-Za-zÀ-ÿ]+)\s*/\s*(\d{4})")

# Tolerância de ponto flutuante na conferência de valores (centavos não contam).
TOLERANCIA = Decimal("0.01")


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    ).lower().strip()


def _competencia_de(nome: str, ano: str) -> Optional[dict]:
    mes = MESES.get(_sem_acento(nome))
    if mes is None:
        return None
    return {"ano": int(ano), "mes": mes}


def ler_periodo_declarado(texto: str) -> tuple[Optional[dict], Optional[str]]:
    """Período que o PDF declara e de onde foi lido.

    Preferência é pela competência de USO (é a que o nome do arquivo
    representa); a de publicação é o fallback.
    """
    if not texto:
        return None, None
    for nome, ano in RE_USO.findall(texto):
        competencia = _competencia_de(nome, ano)
        if competencia:
            return competencia, "uso"
    linhas = texto.splitlines()
    for linha in reversed(linhas):          # o rótulo costuma estar no topo
        achados = RE_PUBLICACAO.findall(linha)
        if achados:
            nome, ano = achados[-1]
            competencia = _competencia_de(nome, ano)
            if competencia:
                return competencia, "publicacao"
    return None, None


def conferir_periodo(texto: str, ano: int, mes: int) -> dict:
    """Compara a competência declarada no PDF com a pedida."""
    declarado, fonte = ler_periodo_declarado(texto)
    if declarado is None:
        return {
            "resultado": INDETERMINADO,
            "pedido": {"ano": ano, "mes": mes},
            "declarado": None,
            "fonte": None,
            "detalhe": "PDF sem rótulo de competência legível",
        }
    bate = declarado["ano"] == ano and declarado["mes"] == mes
    return {
        "resultado": CONFERE if bate else DIVERGENTE,
        "pedido": {"ano": ano, "mes": mes},
        "declarado": declarado,
        "fonte": fonte,
        "detalhe": (
            "competência declarada confere com o pedido" if bate else
            f"a fonte declara {declarado['ano']}-{declarado['mes']:02d} e foi pedido "
            f"{ano}-{mes:02d} — arquivo de outra competência"
        ),
    }


def conferir_gravacao(
    registros: Iterable[Mapping[str, Any]],
    gravados: Mapping[tuple, Any],
) -> dict:
    """C2: confere o que foi **gravado** com o que o PDF disse.

    `gravados` mapeia ``(codigo_padrao, desoneracao)`` para o valor lido de
    volta do banco. Só entra o que foi efetivamente gravado — o que foi para
    quarentena não estava lá, e ausência não é divergência.
    """
    conferidos = 0
    divergencias: list[dict] = []
    for registro in registros:
        chave = (registro.get("codigo_padrao"), registro.get("desoneracao"))
        if chave not in gravados:
            continue
        conferidos += 1
        esperado = registro.get("valor_m2")
        obtido = gravados[chave]
        if esperado is None or obtido is None:
            continue
        if abs(Decimal(str(obtido)) - Decimal(str(esperado))) > TOLERANCIA:
            divergencias.append({
                "codigo_padrao": registro.get("codigo_padrao"),
                "desoneracao": registro.get("desoneracao"),
                "esperado": str(esperado),
                "gravado": str(obtido),
            })
    return {
        "resultado": DIVERGENTE if divergencias else CONFERE,
        "conferidos": conferidos,
        "divergentes": len(divergencias),
        "divergencias": divergencias,
    }


def _competencia_texto(competencia: Mapping[str, Any]) -> str:
    """'AAAA-MM' quando dá; 'competência desconhecida' quando não dá."""
    ano, mes = competencia.get("ano"), competencia.get("mes")
    if ano and mes:
        return f"{int(ano)}-{int(mes):02d}"
    return "desconhecida"


def decidir(conferencia_periodo: Mapping[str, Any]) -> dict:
    """Regra de gravação a partir da conferência de período.

    ``divergente`` não grava: um mês ausente é melhor que um mês carregado com
    o valor de outra competência — e aqui o alerta tem FATO.
    ``indeterminado`` grava: não se bloqueia carga por ignorância.
    """
    resultado = conferencia_periodo.get("resultado")
    if resultado == DIVERGENTE:
        declarado = conferencia_periodo.get("declarado") or {}
        pedido = conferencia_periodo.get("pedido") or {}
        return {
            "gravar": False,
            "conferivel": True,
            "status": "CONFERIU_DIVERGENTE",
            "motivo": (
                f"fonte declara {_competencia_texto(declarado)}, pedido "
                f"{_competencia_texto(pedido)}: competência errada"
            ),
        }
    if resultado == CONFERE:
        return {"gravar": True, "conferivel": True, "status": "SUCESSO", "motivo": None}
    return {
        "gravar": True,
        "conferivel": False,
        "status": "SUCESSO",
        "motivo": "período não conferível no PDF (gravado sem conferência de rótulo)",
    }
