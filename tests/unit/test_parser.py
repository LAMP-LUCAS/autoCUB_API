import pytest
from decimal import Decimal
from autocub.processor.parser import parse_cub_pdf


@pytest.mark.unit
def test_parser_extracts_all_19_nbr_projects(sample_pdf_path):
    """Testa unitariamente a extração determinística dos 19 projetos da NBR 12.721:2006."""
    relatorio = parse_cub_pdf(
        source=str(sample_pdf_path),
        uf="GO",
        sinduscon_id=10,
        desoneracao="SEM_DESONERACAO"
    )

    assert relatorio.ano == 2026
    assert relatorio.mes == 1
    assert relatorio.mes_nome == "Janeiro"
    assert relatorio.data_referencia.isoformat() == "2026-01-01"
    assert len(relatorio.itens) == 19

    itens_map = {item.codigo_canonico: item for item in relatorio.itens}

    expected_codes = [
        "R1-B", "PP-4-B", "R8-B", "PIS",
        "R1-N", "PP-4-N", "R8-N", "R16-N",
        "R1-A", "R8-A", "R16-A",
        "CAL-8-N", "CSL-8-N", "CSL-16-N",
        "CAL-8-A", "CSL-8-A", "CSL-16-A",
        "RP1Q", "GI"
    ]

    for code in expected_codes:
        assert code in itens_map, f"Projeto NBR {code} ausente na extração."

    # Validação de valores exatos
    assert itens_map["R1-B"].valor_m2 == Decimal("2208.73")
    assert itens_map["R1-B"].variacao_pct == Decimal("0.17")
    assert itens_map["R1-N"].valor_m2 == Decimal("2667.75")
    assert itens_map["R1-A"].valor_m2 == Decimal("3287.53")
    assert itens_map["RP1Q"].valor_m2 == Decimal("2229.89")
    assert itens_map["GI"].valor_m2 == Decimal("1202.30")
