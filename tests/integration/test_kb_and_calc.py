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
    # STORY-MCP-007/C-04: `payload` é sempre OBJETO — a forma-lista perdia a UF.
    payload = {
        "itens": [
            {"ambiente": "Apartamento Tipo", "area_real_m2": 100.0},
            {"ambiente": "Garagem Coberta", "area_real_m2": 25.0},
            {"ambiente": "Varanda", "area_real_m2": 10.0}
        ]
    }
    resp = api_client.post("/v1/calc/area", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["area_real_total_m2"]) == 135.0
    # 100*1.0 + 25*0.65 (16.25) + 10*0.50 (5.0) = 121.25
    assert float(data["area_equivalente_total_m2"]) == 121.25
    assert float(data["fator_equivalente_medio"]) < 1.0
    # sem `cub_m2` nem `uf`, o orçamento não sai — e o motivo é nomeado
    assert data["custo_estimado_total"] is None
    assert data["erro"] == "CUB_NAO_INFORMADO"
    assert "cub_m2" in data["motivo"]


@pytest.mark.integration
def test_calc_area_rejeita_payload_lista(api_client):
    """C-04: a forma-lista foi removida (perdia a UF e devolveva custo null)."""
    resp = api_client.post("/v1/calc/area", json=[
        {"ambiente": "Sala", "area_real_m2": 50.0}
    ])
    assert resp.status_code == 422


@pytest.mark.integration
def test_calc_area_sem_cub_explica_e_sugere(api_client, db_session):
    """C-04: orçamento em branco nunca em silêncio — `erro` + `motivo` + UFs.

    O seed dos testes não cria cotações (`cub_mensal`); semeamos uma para GO de
    modo que a sugestão de UF alternativa tenha o que sugerir.
    """
    _semeia_cotacao_go(db_session)

    resp = api_client.post("/v1/calc/area", json={
        "uf": "SP",
        "itens": [{"ambiente": "Sala", "area_real_m2": 50.0}],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["cub_m2_aplicado"] is None
    assert data["custo_estimado_total"] is None
    assert data["erro"] == "CUB_INDISPONIVEL_PARA_UF"
    assert "SP" in data["motivo"]
    assert "GO" in data["ufs_com_cub_mais_proximas"]


@pytest.mark.integration
def test_calc_area_resolve_cub_pela_uf(api_client, db_session):
    """C-04: `uf` sozinha resolve o CUB (antes exigia `uf` + `codigo_padrao`)."""
    _semeia_cotacao_go(db_session)

    resp = api_client.post("/v1/calc/area", json={
        "uf": "GO",
        "itens": [{"ambiente": "Sala", "area_real_m2": 50.0}],
    })
    assert resp.status_code == 200
    data = resp.json()
    # `float()` por tolerância: a tipagem numérica é do ADR 009/X-01 (Onda 3),
    # coberta pelo claim do gate; aqui o que importa é RESOLVER o CUB pela UF.
    assert float(data["cub_m2_aplicado"]) > 0
    assert float(data["custo_estimado_total"]) > 0
    assert data["erro"] is None


def _semeia_cotacao_go(session) -> None:
    """Cotação mínima para GO — o seed criaponsors mas não `cub_mensal`."""
    from datetime import date

    from autocub.database.models import CubMensal, Sinduscon

    go = session.query(Sinduscon).filter(Sinduscon.uf == "GO").first()
    assert go is not None, "seed sem UF GO"
    session.add(CubMensal(
        sinduscon_id=go.id,
        data_referencia=date(2026, 7, 1),
        codigo_padrao="R8-N",
        desoneracao="SEM_DESONERACAO",
        valor_m2=Decimal("2158.03"),
        variacao_mensal_pct=Decimal("1.20"),
    ))
    session.commit()


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

