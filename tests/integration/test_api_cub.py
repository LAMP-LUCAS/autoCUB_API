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
                "data_referencia": date(2026, 1, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "COM_DESONERACAO",
                "valor_m2": Decimal("2450.00"),
                "variacao_mensal_pct": Decimal("0.25")
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
    # Validação da origem completa
    assert data_uf[0]["cotacoes"][0]["uf"] == "GO"
    assert data_uf[0]["cotacoes"][0]["sinduscon_nome"] == "Sinduscon-GO"
    assert data_uf[0]["cotacoes"][0]["regiao"] == "CENTRO-OESTE"

    # 2. Latest com Origem Completa
    resp_latest = api_client.get("/v1/cub/latest?uf=GO")
    assert resp_latest.status_code == 200
    data_latest = resp_latest.json()
    assert len(data_latest) >= 1
    assert data_latest[0]["uf"] == "GO"
    assert data_latest[0]["sinduscon_nome"] == "Sinduscon-GO"
    assert data_latest[0]["regiao"] == "CENTRO-OESTE"

    # 3. Consulta Série Histórica com Indicadores Pré-calculados
    resp_hist = api_client.get("/v1/cub/GO/historico/R1-N")
    assert resp_hist.status_code == 200
    data_hist = resp_hist.json()
    assert data_hist["total_meses"] == 2
    assert float(data_hist["serie_historica"][0]["valor_m2"]) == 2667.75
    assert data_hist["valor_inicial"] is not None
    assert data_hist["valor_final"] is not None
    assert data_hist["variacao_acumulada_periodo_pct"] is not None

    # 4. Comparativo Regional
    resp_comp = api_client.get("/v1/cub/comparativo?ufs=GO,MG&codigo_padrao=R1-N&ano=2026&mes=1")
    assert resp_comp.status_code == 200
    data_comp = resp_comp.json()
    ufs = [c["uf"] for c in data_comp["comparativo"]]
    assert "GO" in ufs
    assert "MG" in ufs
    assert data_comp["total_comparados"] == 2
    assert float(data_comp["media_grupo"]) > 0

    # 5. Panorama Analítico e Estrutura Agrupada
    resp_pan = api_client.get("/v1/cub/GO/panorama?ano=2026&mes=1")
    assert resp_pan.status_code == 200
    data_pan = resp_pan.json()
    assert data_pan["uf"] == "GO"
    assert data_pan["sinduscon_nome"] == "Sinduscon-GO"
    assert "media_geral_m2" in data_pan["metricas"]
    assert "residencial" in data_pan["estrutura_agrupada"]
    assert "comercial" in data_pan["estrutura_agrupada"]

    # 6. Impacto da Desoneração
    resp_deson = api_client.get("/v1/cub/GO/impacto-desoneracao?ano=2026&mes=1")
    assert resp_deson.status_code == 200
    data_deson = resp_deson.json()
    assert data_deson["uf"] == "GO"
    assert float(data_deson["economia_media_reais_m2"]) > 0
    assert float(data_deson["economia_media_percentual"]) > 0
    assert len(data_deson["projetos"]) == 1
    assert data_deson["projetos"][0]["codigo_padrao"] == "R1-N"

    # 7. Ranking Nacional
    resp_rank = api_client.get("/v1/cub/ranking?codigo_padrao=R1-N&ano=2026&mes=1")
    assert resp_rank.status_code == 200
    data_rank = resp_rank.json()
    assert data_rank["total_estados"] == 2
    assert len(data_rank["ranking"]) == 2
    assert data_rank["ranking"][0]["posicao"] == 1
    assert data_rank["ranking"][0]["desvio_media_pct"] is not None

