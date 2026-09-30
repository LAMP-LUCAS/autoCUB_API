"""
Tipo numérico de fronteira — ADR 009 (JSON number).

Mesma decisão do AutoINCC (mesmo ADR, mesma causa): o Pydantic v2 serializa
`Decimal` como `str`, e o AutoCUB entregava
`{"custo_estimado_total": "102894.53", "area_real_total_m2": "33.10"}`.
O agente e a planilha precisam parsear texto antes de somar.

    Num = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

Regras (ADR 009):
1. **Cálculo continua em `Decimal`** — CUB/m², área equivalente, ponderações
   NBR 12.721, variação mensal. O tipo é usado só em schema de RESPOSTA.
2. Datas continuam string ISO.
3. O cache da API usa `model_dump(mode="json")` — vale para o cache junto.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

Num = Annotated[
    Decimal,
    PlainSerializer(float, return_type=float, when_used="json"),
]
