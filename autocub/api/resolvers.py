"""Resolução determinística de Sinduscon (§5.1 da auditoria de custo).

Default único para TODOS os endpoints: sinduscon **ativo** da UF com o
**dado mais recente** (empate → menor id). Antes do fix cada endpoint
resolvia o default silenciosamente à sua maneira (`.first()` sem ordem):
o histórico resolvia Sinduscon-MG (id 1, parado em 2026-06) enquanto o
ranking mostrava MG via Sinduscon-GV (id 39, 2026-08) — e as linhas do
ranking nem sequer traziam `sinduscon_id` (divergência de ~20% entre
respostas do mesmo UF+padrão; gate da casa §5.1: id=1 × id=None).
"""

from datetime import date
from typing import Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from autocub.database.models import CubMensal, Sinduscon


def max_data_por_sinduscon(db: Session) -> Dict[int, Optional[date]]:
    """Última data de referência existente por sinduscon (qualquer padrão/regime)."""
    rows = (
        db.query(CubMensal.sinduscon_id, func.max(CubMensal.data_referencia))
        .group_by(CubMensal.sinduscon_id)
        .all()
    )
    return {sid: mx for sid, mx in rows}


def chave_preferencia(
    sinduscon_id: int,
    ativo: bool,
    maxes: Dict[int, Optional[date]],
):
    """Ordem de preferência total e determinística: ativo > com dado >
    dado mais recente > menor id. Usada tanto no default de uma UF
    quanto na escolha, dentro de cada UF, da linha de ranking/comparativo."""
    mx = maxes.get(sinduscon_id)
    return (
        not ativo,
        mx is None,
        -(mx.toordinal() if mx else 0),
        sinduscon_id,
    )


def resolver_sinduscon(
    db: Session,
    uf: str,
    sinduscon_id: Optional[int] = None,
    maxes: Optional[Dict[int, Optional[date]]] = None,
) -> Optional[Sinduscon]:
    """Resolve o Sinduscon de uma UF de forma determinística (§5.1).

    - `sinduscon_id` explícito → esse sinduscon (precisa estar ativo na UF);
    - default único: sinduscon **ativo** com o **dado mais recente**
      (empate → menor id).

    Retorna ``None`` se a UF não tiver sinduscon ativo — o chamador decide
    o 404 (cada endpoint preserva a própria mensagem).

    ``maxes``: mapa opcional sinduscon_id → última data de referência
    (evita refazer a agregação quando um endpoint resolve vários sinduscons).
    """
    uf_upper = uf.upper()
    query = db.query(Sinduscon).filter(
        Sinduscon.uf == uf_upper,
        Sinduscon.ativo == True,  # noqa: E712
    )
    if sinduscon_id is not None:
        return query.filter(Sinduscon.id == sinduscon_id).first()

    cands = query.all()
    if not cands:
        return None
    if maxes is None:
        maxes = max_data_por_sinduscon(db)
    return sorted(cands, key=lambda s: chave_preferencia(s.id, s.ativo, maxes))[0]
