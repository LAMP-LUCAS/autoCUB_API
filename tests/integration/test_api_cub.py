import pytest
from datetime import date
from decimal import Decimal
from autocub.database.loader import upsert_cub_records


@pytest.mark.integration
def test_health_check_endpoint(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "database" in data


@pytest.mark.integration
def test_list_padroes_endpoint(api_client):
    response = api_client.get("/v1/padroes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 19
    codes = [item["codigo"] for item in data]
    assert "R1-B" in codes
    assert "R1-N" in codes
    assert "R1-A" in codes
    assert "GI" in codes


@pytest.mark.integration
def test_list_sinduscons_endpoint(api_client):
    response = api_client.get("/v1/sinduscons?uf=GO")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["uf"] == "GO"
    assert data[0]["id"] == 10


@pytest.mark.integration
def test_cub_queries_and_comparativo(api_client, db_session):
    # Insere dados de teste
    upsert_cub_records(
        db_session,
        [
            {
                "sinduscon_id": 10,  # GO
                "data_referencia": date(2026, 1, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("2667.75"),
                "variacao_mensal_pct": Decimal("0.28")
            },
            {
                "sinduscon_id": 10,  # GO
                "data_referencia": date(2026, 2, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("2690.00"),
                "variacao_mensal_pct": Decimal("0.83")
            },
            {
                "sinduscon_id": 1,  # MG
                "data_referencia": date(2026, 1, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("2750.50"),
                "variacao_mensal_pct": Decimal("0.45")
            }
        ]
    )

    # 1. Consulta CUB por UF
    resp_uf = api_client.get("/v1/cub/GO?ano=2026&mes=1")
    assert resp_uf.status_code == 200
    data_uf = resp_uf.json()
    assert len(data_uf) == 1
    assert data_uf[0]["uf"] == "GO"
    assert data_uf[0]["cotacoes"][0]["codigo_padrao"] == "R1-N"

    # 2. Consulta Série Histórica
    resp_hist = api_client.get("/v1/cub/GO/historico/R1-N")
    assert resp_hist.status_code == 200
    data_hist = resp_hist.json()
    assert data_hist["total_meses"] == 2
    assert float(data_hist["serie_historica"][0]["valor_m2"]) == 2667.75

    # 3. Comparativo Regional
    resp_comp = api_client.get("/v1/cub/comparativo?ufs=GO,MG&codigo_padrao=R1-N&ano=2026&mes=1")
    assert resp_comp.status_code == 200
    data_comp = resp_comp.json()
    ufs = [c["uf"] for c in data_comp["comparativo"]]
    assert "GO" in ufs
    assert "MG" in ufs
