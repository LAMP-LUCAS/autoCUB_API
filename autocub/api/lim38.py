"""LIM-38 — cobertura de UF: sinalização da limitação de roadmap.

A auditoria MCP de custo (§5.0) registrou que `cub_sinduscons_list` cobre
**19 das 27 UFs**: nem todos os estados fornecem CUB à CBIC e os adapters
de alguns estados ainda não foram implementados — limitação de roadmap
conhecida, **não é defeito** (o próprio item da auditoria diz isso).

Decisão do usuário (2026-09-30): **nota no response** — responder com a
nota detalhando que o dado *ainda não foi disponibilizado pelo CBIC* e que
a equipe de desenvolvimento está procurando solução, em vez de erro 404
vazio ou ``[]`` vazio (responder > erro/``[]``).

O claim do gate (``claim_lim38``) cobre a **sinalização**, nunca a
cobertura: nenhum teste/gate desta nota afirma quantas UFs têm dado.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from autocub.api.resolvers import resolver_sinduscon

#: As 27 unidades federativas do Brasil — distinguir "UF válida sem
#: adapter" (LIM-38) de código inválido (erro comum, sem nota).
BR_UFS = frozenset({
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG",
    "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR",
    "RS", "SC", "SE", "SP", "TO",
})

NOTA_LIM38 = (
    "Dado de CUB ainda não disponibilizado pelo CBIC para esta UF "
    "(limitação de roadmap LIM-38: alguns estados não publicam o índice e "
    "adapters de outros ainda não foram implementados); a equipe de "
    "desenvolvimento está procurando solução."
)


def uf_sem_adapter(db: Session, uf: str) -> bool:
    """True quando ``uf`` é UF brasileira válida **sem** sinduscon ativo —
    o caso LIM-38. Código inválido (ex.: ``"XX"``) não é cobertura ausente:
    é erro comum e não recebe a nota."""
    return uf.upper() in BR_UFS and resolver_sinduscon(db, uf.upper()) is None


def detalhe_sem_cobertura(base: str, uf: str, db: Session) -> str:
    """Mensagem de 404 acrescida da nota LIM-38 **apenas** quando o caso é
    de fato cobertura ausente (UF válida brasileira sem adapter)."""
    if uf_sem_adapter(db, uf):
        return f"{base} {NOTA_LIM38}"
    return base
