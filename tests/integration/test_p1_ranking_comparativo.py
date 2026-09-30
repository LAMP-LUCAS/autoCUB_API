"""P1 da auditoria — §5.3 e §5.4 (critérios iguais aos do gate da casa
`automation/scripts/verify_mcp_audit_claims.py`).

§5.3: o ranking declara a AMOSTRA da "média nacional" — `ufs_incluidas` +
      `cobertura_pct` (hoje a média é calculada só sobre as UFs com dado na
      data, sem declarar a cobertura; gate: `qualificado = any(media_amostra |
      ufs_incluidas | cobertura_pct)` — RED atual: média qualificada=False).
§5.4: o comparativo sinaliza UF pedida sem dado (SP sem adapter de coleta) —
      `ufs_nao_encontrados` na resposta (gate: dump contém "SP" ou recusa
      citando SP; RED atual: SP simplesmente descartada sem aviso).

Ambiente: testes rodam no container `autocub_api`; o rank é cacheado
(`cub:*` em `autocub-redis`) — zerar o cache antes do run para não servir
resposta de seed anterior.
"""
from datetime import date
from decimal import Decimal

import pytest

from autocub.database.loader import upsert_cub_records


def _seed(db_session) -> None:
    """MG multi-sindicato + GO — mesmo cenário do §5.1 (2026-08 é o mês
    global de referência; SP nunca tem dado)."""
    upsert_cub_records(
        db_session,
        [
            {
                "sinduscon_id": 1,
                "data_referencia": date(2026, 6, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("3071.89"),
                "variacao_mensal_pct": Decimal("0.50"),
            },
            {
                "sinduscon_id": 39,
                "data_referencia": date(2026, 8, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("2443.84"),
                "variacao_mensal_pct": Decimal("0.55"),
            },
            {
                "sinduscon_id": 10,
                "data_referencia": date(2026, 8, 1),
                "codigo_padrao": "R1-N",
                "desoneracao": "SEM_DESONERACAO",
                "valor_m2": Decimal("2690.00"),
                "variacao_mensal_pct": Decimal("0.83"),
            },
        ],
    )


@pytest.mark.integration
def test_ranking_declara_amostra_da_media(api_client, db_session):
    """§5.3: ufs_incluidas + cobertura_pct qualificam a média nacional."""
    _seed(db_session)

    resp = api_client.get("/v1/cub/rank?codigo_padrao=R1-N")
    assert resp.status_code == 200
    data = resp.json()

    ufs = [str(r.get("uf", "")).upper() for r in data["ranking"]]
    assert data["total_estados"] == len(set(ufs))  # pin do dedup do §5.1

    incl = data.get("ufs_incluidas")
    assert incl, "ranking deve declarar ufs_incluidas (§5.3)"
    assert sorted(set(ufs)) == sorted(u.upper() for u in incl)

    cob = data.get("cobertura_pct")
    assert cob is not None, "ranking deve declarar cobertura_pct (§5.3)"
    assert float(cob) == pytest.approx(len(set(ufs)) / 27 * 100, abs=0.1)


@pytest.mark.integration
def test_comparativo_sinaliza_uf_sem_dado(api_client, db_session):
    """§5.4: SP pedida no comparativo → `ufs_nao_encontrados` nomeia SP."""
    _seed(db_session)

    resp = api_client.get(
        "/v1/cub/comparativo?ufs=SP,MG&codigo_padrao=R1-N&ano=2026&mes=8"
    )
    assert resp.status_code == 200
    data = resp.json()

    nao = data.get("ufs_nao_encontrados")
    assert nao is not None, "comparativo deve expor ufs_nao_encontrados (§5.4)"
    assert "SP" in [u.upper() for u in nao], (
        f"SP pedida sem dado deve ser sinalizada, veio: {nao}"
    )
    assert any(str(c.get("uf", "")).upper() == "MG" for c in data["comparativo"]), (
        "MG tem dado em 2026-08 e deve aparecer no comparativo"
    )
