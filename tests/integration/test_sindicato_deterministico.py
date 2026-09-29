"""RED §5.1 — mesmo UF+padrão → mesmo sinduscon (default único e determinístico).

Evidência da auditoria (Fase 0 confirmou via request real): `cub_historico`
resolvia Sinduscon-MG (id 1, dado de 2026-06) enquanto `cub_ranking` mostrava
MG via Sinduscon-GV (id 39, dado de 2026-08) — e as linhas do ranking nem
traziam `sinduscon_id` (gate: `historico(id=1) × ranking MG(id=None)` → FAIL).

Critério GREEN (gate da casa `verify_mcp_audit_claims.py` §5.1):
`hist.sinduscon_id == rank_row.sinduscon_id`, ambos não-nulos, cada resposta
nomeando quem respondeu (id + nome), e uma linha por UF no ranking/comparativo.

Default documentado (§5.1 / plano do repositório): sinduscon **ativo** da UF
com o **dado mais recente** (empate → menor id) — o mesmo critério em todos
os endpoints (inclusive na resolução automática do CUB em `POST /calc/area`).
"""

from datetime import date
from decimal import Decimal

import pytest

from autocub.database.loader import upsert_cub_records


def _seed_mg_multi(db_session) -> None:
    """MG multi-sindicato como na produção: id1 (Sinduscon-MG) parado em
    2026-06 e id39 (Sinduscon-GV) fresco em 2026-08 — além de GO p/ o ranking."""
    upsert_cub_records(
        db_session,
        [
            {
                "sinduscon_id": 1,  # Sinduscon-MG (stale)
                "data_referencia": date(2026, 6, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("3071.89"),
                "variacao_mensal_pct": Decimal("0.50"),
            },
            {
                "sinduscon_id": 39,  # Sinduscon-GV (fresco)
                "data_referencia": date(2026, 6, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("2400.00"),
                "variacao_mensal_pct": Decimal("0.40"),
            },
            {
                "sinduscon_id": 39,  # Sinduscon-GV (fresco)
                "data_referencia": date(2026, 8, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("2443.84"),
                "variacao_mensal_pct": Decimal("0.55"),
            },
            {
                "sinduscon_id": 10,  # Sinduscon-GO
                "data_referencia": date(2026, 8, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("2690.00"),
                "variacao_mensal_pct": Decimal("0.83"),
            },
        ],
    )


@pytest.mark.integration
def test_historico_e_ranking_mg_apontam_o_mesmo_sindicato(api_client, db_session):
    """Condição exata do gate §5.1: id_h e id_r não-nulos e iguais."""
    _seed_mg_multi(db_session)

    hist = api_client.get("/v1/cub/MG/hist/R1-N")
    assert hist.status_code == 200
    hist = hist.json()

    rank = api_client.get("/v1/cub/rank?codigo_padrao=R1-N")
    assert rank.status_code == 200
    rank = rank.json()

    mg_rows = [r for r in rank["ranking"] if str(r.get("uf", "")).upper() == "MG"]
    assert mg_rows, "ranking nacional deve conter MG"
    assert len(mg_rows) == 1, "ranking deve ter exatamente uma linha por UF (default único)"

    id_h = hist.get("sinduscon_id")
    id_r = mg_rows[0].get("sinduscon_id")
    assert id_h is not None and id_r is not None and id_h == id_r, (
        f"historico(id={id_h}, {hist.get('sinduscon_nome')}) × "
        f"ranking MG(id={id_r}, {mg_rows[0].get('sinduscon_nome')})"
    )


@pytest.mark.integration
def test_ranking_e_comparativo_uma_linha_por_uf_nomeando_o_respondente(api_client, db_session):
    """Quando DOIS sinduscons ativos da UF têm dado no mês de referência, o
    ranking/comparativo mostram UMA linha por UF (o default) e trazem
    `sinduscon_id` + `sinduscon_nome`."""
    _seed_mg_multi(db_session)
    upsert_cub_records(
        db_session,
        [
            {  # id1 também fresco em 2026-08 → dois candidatos no ranking
                "sinduscon_id": 1,
                "data_referencia": date(2026, 8, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("3100.00"),
                "variacao_mensal_pct": Decimal("0.94"),
            },
        ],
    )

    rank = api_client.get("/v1/cub/rank?codigo_padrao=R1-N").json()
    ufs = [str(r.get("uf", "")).upper() for r in rank["ranking"]]
    mg_rows = [r for r in rank["ranking"] if str(r.get("uf", "")).upper() == "MG"]
    assert len(mg_rows) == 1, f"MG duplicado no ranking: {mg_rows}"
    assert len(ufs) == len(set(ufs)), f"UF repetida no ranking: {ufs}"
    assert rank["total_estados"] == len(rank["ranking"])
    assert mg_rows[0].get("sinduscon_id") is not None, "linha do ranking deve trazer sinduscon_id"

    comp = api_client.get(
        "/v1/cub/comparativo?ufs=MG,GO&codigo_padrao=R1-N&ano=2026&mes=8"
    )
    assert comp.status_code == 200
    comp = comp.json()
    comp_mg = [c for c in comp["comparativo"] if str(c.get("uf", "")).upper() == "MG"]
    assert len(comp_mg) == 1, f"MG duplicado no comparativo: {comp_mg}"
    assert comp_mg[0].get("sinduscon_id") is not None, "item do comparativo deve trazer sinduscon_id"


@pytest.mark.integration
def test_default_unico_em_todos_os_endpoints_de_uf(api_client, db_session):
    """Histórico, panorama e impacto de desoneração resolvem o MESMO default
    documentado: sinduscon ativo com dado mais recente (aqui: GV, id 39)."""
    _seed_mg_multi(db_session)

    hist = api_client.get("/v1/cub/MG/hist/R1-N")
    pan = api_client.get("/v1/cub/MG/panorama")
    des = api_client.get("/v1/cub/MG/impacto-desoneracao")
    assert hist.status_code == 200 and pan.status_code == 200 and des.status_code == 200
    hist, pan, des = hist.json(), pan.json(), des.json()

    assert hist.get("sinduscon_id") == 39, f"default do histórico: {hist.get('sinduscon_nome')}"
    assert pan.get("sinduscon_id") == 39, f"default do panorama: {pan.get('sinduscon_nome')}"
    assert des.get("sinduscon_id") == 39, f"default da desoneração: {des.get('sinduscon_nome')}"
    assert hist["sinduscon_id"] == pan["sinduscon_id"] == des["sinduscon_id"]


@pytest.mark.integration
def test_calc_area_usa_o_mesmo_default_de_cub(api_client, db_session):
    """A resolução automática de CUB (uf+padrão) em POST /calc/area segue o
    MESMO default documentado — hoje resolvia o sinduscon parado (id 1)."""
    _seed_mg_multi(db_session)

    resp = api_client.post(
        "/v1/calc/area",
        json={
            "uf": "MG",
            "codigo_padrao": "R1-N",
            "itens": [
                {"ambiente": "Apartamento Privativo", "area_real_m2": 100.0, "fator_ponderacao": 1.0}
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    # CUB do default (Sinduscon-GV, 2026-08) e não do sinduscon parado em 2026-06
    assert float(data["cub_m2_aplicado"]) == pytest.approx(2443.84, rel=1e-6)
