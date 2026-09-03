import pytest
from decimal import Decimal
from autocub.processor.parser import parse_cub_pdf
from autocub.database.loader import upsert_cub_records


@pytest.mark.e2e
def test_full_pipeline_ingestion_to_api_e2e(sample_pdf_path, db_session, api_client):
    """
    Teste End-to-End do pipeline completo:
    PDF Bruto Oficial -> Parser Vetorial -> Upsert no Banco -> Consulta HTTP na API REST.
    """
    # 1. Extração do PDF oficial
    relatorio = parse_cub_pdf(
        source=str(sample_pdf_path),
        uf="GO",
        sinduscon_id=10,
        desoneracao="SEM_DESONERACAO"
    )
    assert len(relatorio.itens) == 19

    # 2. Carga idempotente no banco de dados
    records = [
        {
            "sinduscon_id": 10,
            "data_referencia": relatorio.data_referencia,
            "codigo_padrao": item.codigo_canonico,
            "desoneracao": "SEM_DESONERACAO",
            "valor_m2": item.valor_m2,
            "variacao_mensal_pct": item.variacao_pct
        }
        for item in relatorio.itens
    ]
    count = upsert_cub_records(db_session, records)
    assert count == 19

    # 3. Consulta ponta a ponta via API RESTful
    response = api_client.get("/v1/cub/GO?ano=2026&mes=1&desoneracao=SEM_DESONERACAO")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    uf_periodo = data[0]
    assert uf_periodo["uf"] == "GO"
    assert uf_periodo["total_projetos"] == 19
    assert uf_periodo["data_referencia"] == "2026-01-01"

    # Mapeia cotações retornadas pela API HTTP
    cotacoes_map = {c["codigo_padrao"]: Decimal(str(c["valor_m2"])) for c in uf_periodo["cotacoes"]}

    # Validações dos valores finais entregues pela API
    assert cotacoes_map["R1-B"] == Decimal("2208.73")
    assert cotacoes_map["R1-N"] == Decimal("2667.75")
    assert cotacoes_map["R1-A"] == Decimal("3287.53")
    assert cotacoes_map["GI"] == Decimal("1202.30")
    assert cotacoes_map["RP1Q"] == Decimal("2229.89")
