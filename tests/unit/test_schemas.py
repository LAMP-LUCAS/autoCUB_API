import pytest
from datetime import date
from decimal import Decimal
from autocub.processor.schemas import (
    CubItemExtracted,
    CubRelatorioExtracted,
    PadraoResponse,
    SindusconResponse
)


@pytest.mark.unit
def test_cub_item_extracted_schema():
    item = CubItemExtracted(
        categoria="RESIDENCIAL",
        padrao="NORMAL",
        codigo_base="R-1",
        codigo_canonico="R1-N",
        valor_m2=Decimal("2667.75"),
        variacao_pct=Decimal("0.28")
    )
    assert item.codigo_canonico == "R1-N"
    assert item.valor_m2 == Decimal("2667.75")
    assert item.variacao_pct == Decimal("0.28")


@pytest.mark.unit
def test_padrao_response_schema():
    padrao = PadraoResponse(
        codigo="R1-N",
        codigo_base="R-1",
        nome="Residência Unifamiliar Normal",
        categoria="RESIDENCIAL",
        padrao_acabamento="NORMAL",
        pavimentos=1,
        descricao="Casa térrea padrão normal."
    )
    assert padrao.codigo == "R1-N"
    assert padrao.pavimentos == 1
