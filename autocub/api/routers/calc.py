from decimal import Decimal
from typing import List
from fastapi import APIRouter
from autocub.processor.schemas import AreaItemInput, AreaItemOutput, AreaEquivalenteResponse

router = APIRouter(prefix="/calc", tags=["Calculadoras Paramétricas Normativas"])

# Tabela canônica de fatores padrão (NBR 12.721 Quadro II)
FATORES_PADRAO = {
    "privativa": Decimal("1.00"),
    "apartamento": Decimal("1.00"),
    "sala": Decimal("1.00"),
    "garagem coberta": Decimal("0.65"),
    "garagem descoberta": Decimal("0.12"),
    "estacionamento": Decimal("0.12"),
    "varanda": Decimal("0.50"),
    "sacada": Decimal("0.50"),
    "terraco": Decimal("0.30"),
    "area servico descoberta": Decimal("0.30"),
    "pilotis": Decimal("0.40"),
}


def resolver_fator(nome_ambiente: str) -> Decimal:
    nome_norm = nome_ambiente.lower()
    for k, v in FATORES_PADRAO.items():
        if k in nome_norm:
            return v
    return Decimal("1.00")


@router.post("/area", response_model=AreaEquivalenteResponse, summary="Calculadora de Área Equivalente de Construção (NBR 12.721)")
def calcular_area_equivalente(itens: List[AreaItemInput]):
    """
    Calcula a Área Equivalente de Construção (Quadro II da ABNT NBR 12.721)
    a partir das áreas reais de cada ambiente. A área equivalente resultante é a que
    deve ser multiplicada pelo CUB/m² para obter a estimativa correta de custo.
    """
    outputs: List[AreaItemOutput] = []
    total_real = Decimal("0.00")
    total_equiv = Decimal("0.00")

    for item in itens:
        fator = item.fator_ponderacao if item.fator_ponderacao is not None else resolver_fator(item.ambiente)
        area_eq = round(item.area_real_m2 * fator, 2)

        total_real += item.area_real_m2
        total_equiv += area_eq

        outputs.append(
            AreaItemOutput(
                ambiente=item.ambiente,
                area_real_m2=item.area_real_m2,
                fator_utilizado=fator,
                area_equivalente_m2=area_eq
            )
        )

    fator_medio = round(total_equiv / total_real, 4) if total_real > 0 else Decimal("1.0000")

    return AreaEquivalenteResponse(
        area_real_total_m2=total_real,
        area_equivalente_total_m2=total_equiv,
        fator_equivalente_medio=fator_medio,
        itens=outputs
    )
