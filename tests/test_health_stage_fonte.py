"""RED §5.8 (auditoria MCP de custo) — health com `stage` + mapa `fontes`.

O health reportava `environment: "development"` numa API que serve dado de
custo usado em decisão comercial, e não dizia qual é a origem do dado por UF.
Contrato aprovado (Fase 5, 2026-09-30):

- `stage` substitui `environment` (valor declarado na implantação via env
  `STAGE`; default de desenvolvimento preservado para instâncias locais);
- `fontes`: mapa UF → sindicatos que **efetivamente publicaram** cotação —
  derivado de dado publicado, não do cadastro: UF sem cotação não aparece,
  coerente com a sinalização LIM-38 da Etapa 4 ("dado ainda não disponibilizado
  pelo CBIC").
"""
from datetime import date
from decimal import Decimal

from autocub.core.config import settings
from autocub.database.loader import upsert_cub_records


def test_health_reporta_stage_e_fontes(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    # `stage` substitui `environment` (RED: hoje só existe "environment")
    assert "stage" in data
    assert data["stage"] == settings.STAGE
    assert "environment" not in data

    # mapa `fontes` por UF presente e com forma estável
    assert isinstance(data.get("fontes"), dict)


def test_health_fontes_deriva_de_dado_publicado(api_client, db_session):
    # MG tem cotação publicada (Sinduscon-MG, id 1); SP não tem dado algum
    upsert_cub_records(db_session, [{
        "sinduscon_id": 1,
        "data_referencia": date(2026, 1, 1),
        "codigo_padrao": "R1-N",
        "desoneracao": "SEM_DESONERACAO",
        "valor_m2": Decimal("2500.00"),
        "variacao_mensal_pct": Decimal("0.5"),
    }])

    data = api_client.get("/health").json()

    # RED: chave "fontes" não existe hoje
    assert data["fontes"].get("MG") == ["Sinduscon-MG"]
    assert "SP" not in data["fontes"]  # sem dado publicado → sem fonte
