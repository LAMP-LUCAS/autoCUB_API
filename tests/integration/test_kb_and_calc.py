import pytest
from decimal import Decimal


@pytest.mark.integration
def test_kb_faq_endpoint(api_client):
    resp = api_client.get("/v1/kb/faq")
    assert resp.status_code == 200
    data = resp.json()
    assert "itens_excluidos_do_cub" in data
    assert "faq" in data
    assert len(data["itens_excluidos_do_cub"]) >= 8
    # Verifica exclusão de fundações e terreno
    itens = [i["item"].lower() for i in data["itens_excluidos_do_cub"]]
    assert any("fundações" in i for i in itens)
    assert any("terreno" in i for i in itens)


@pytest.mark.integration
def test_kb_insumos_endpoint(api_client):
    resp = api_client.get("/v1/kb/insumos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_insumos"] == 29
    assert len(data["insumos"]) == 29
    assert "familias_macro_percentuais" in data


@pytest.mark.integration
def test_kb_lei_endpoint(api_client):
    resp = api_client.get("/v1/kb/lei")
    assert resp.status_code == 200
    data = resp.json()
    assert "Lei Federal 4.591" in data["lei"]
    assert "art_54" in data["artigos"]
    assert "jurisprudencia_stj" in data


@pytest.mark.integration
def test_kb_nbr_endpoint(api_client):
    resp = api_client.get("/v1/kb/nbr")
    assert resp.status_code == 200
    data = resp.json()
    assert "fatores_area_equivalente" in data
    assert len(data["fatores_area_equivalente"]) >= 5


@pytest.mark.integration
def test_calc_area_equivalente_endpoint(api_client):
    payload = [
        {"ambiente": "Apartamento Tipo", "area_real_m2": 100.0},
        {"ambiente": "Garagem Coberta", "area_real_m2": 25.0},
        {"ambiente": "Varanda", "area_real_m2": 10.0}
    ]
    resp = api_client.post("/v1/calc/area", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["area_real_total_m2"]) == 135.0
    # 100*1.0 + 25*0.65 (16.25) + 10*0.50 (5.0) = 121.25
    assert float(data["area_equivalente_total_m2"]) == 121.25
    assert float(data["fator_equivalente_medio"]) < 1.0


@pytest.mark.integration
def test_padrao_has_architectural_fields(api_client):
    resp = api_client.get("/v1/padroes/R1-N")
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["area_real"]) == 106.44
    assert float(data["area_equivalente"]) == 99.47
    assert data["dormitorios"] == 3
    assert data["vagas_garagem"] == 1


@pytest.mark.integration
def test_calc_fatores_endpoint(api_client):
    resp = api_client.get("/v1/calc/fatores")
    assert resp.status_code == 200
    data = resp.json()
    assert "fatores" in data
    assert len(data["fatores"]) >= 6
    assert any("Garagem" in f["tipo_ambiente"] for f in data["fatores"])


@pytest.mark.integration
def test_calc_area_com_cub_m2_estimativa_custo(api_client):
    payload = {
        "cub_m2": 2000.0,
        "itens": [
            {"ambiente": "Apartamento Privativo", "area_real_m2": 100.0, "fator_ponderacao": 1.0},
            {"ambiente": "Garagem Coberta", "area_real_m2": 20.0, "fator_ponderacao": 0.65}
        ]
    }
    resp = api_client.post("/v1/calc/area", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # area equiv: 100 + 13 = 113 m²
    assert float(data["area_equivalente_total_m2"]) == 113.0
    # custo total: 113 * 2000 = 226000.0
    assert float(data["custo_estimado_total"]) == 226000.0
    assert float(data["cub_m2_aplicado"]) == 2000.0

