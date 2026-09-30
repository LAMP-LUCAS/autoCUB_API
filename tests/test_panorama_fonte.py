"""RED §5.8 (auditoria MCP de custo) — panorama expõe `fonte` por UF.

A resposta canônica por UF (`/v1/cub/{uf}/dash`, tool `cub_panorama`)
expunha sinduscon/data em campos separados, sem uma sinalização única de
origem que o agente possa repassar ao usuário. Contrato aprovado: campo
`fonte` em texto — sindicato publicador, norma e período de referência.
"""
from datetime import date
from decimal import Decimal

from autocub.database.loader import upsert_cub_records


def test_panorama_expoe_fonte_de_origem(api_client, db_session):
    upsert_cub_records(db_session, [{
        "sinduscon_id": 1,  # Sinduscon-MG
        "data_referencia": date(2026, 1, 1),
        "codigo_padrao": "R1-N",
        "desoneracao": "SEM_DESONERACAO",
        "valor_m2": Decimal("2500.00"),
        "variacao_mensal_pct": Decimal("0.5"),
    }])

    resp = api_client.get("/v1/cub/MG/dash")
    assert resp.status_code == 200  # RED: 500 (fonte ausente no construtor)
    data = resp.json()

    fonte = data.get("fonte")  # RED: KeyError → None
    assert fonte is not None
    assert "Sinduscon-MG" in fonte
    assert "MG" in fonte
    assert "NBR 12.721" in fonte
    assert "2026-01" in fonte
