"""RED §5.6 (auditoria MCP de custo) — /v1/cub/latest paginado.

Em produção `cub_latest()` sem filtro devolvia o blob completo (auditoria:
4.269 linhas / 361 registros impressos como JSON multi-objeto), estourando a
janela de contexto do agente com um único call. Contrato aprovado pelo
usuário (Fase 5, 2026-09-30): `limit` com **default 50**, **`0` = ilimitado**,
personalizável na consulta."""
from datetime import date
from decimal import Decimal

from autocub.database.loader import upsert_cub_records
from autocub.database.models import PadraoProjeto

SINDUSCONS_TESTE = (8, 10, 13)  # DF, GO, MT (ativos no seed)


def _seed_57(db_session) -> int:
    """3 sinduscons × 19 padrões = 57 cotações (acima do default de 50)."""
    padroes = [p.codigo for p in db_session.query(PadraoProjeto).all()]
    assert len(padroes) == 19, f"seed deveria ter 19 padrões, tem {len(padroes)}"
    registros = [
        {
            "sinduscon_id": sid,
            "data_referencia": date(2026, 1, 1),
            "codigo_padrao": cod,
            "desoneracao": "SEM_DESONERACAO",
            "valor_m2": Decimal("2500.00"),
            "variacao_mensal_pct": Decimal("0.5"),
        }
        for sid in SINDUSCONS_TESTE
        for cod in padroes
    ]
    upsert_cub_records(db_session, registros)
    return len(registros)


def test_latest_default_limita_a_50(api_client, db_session):
    """§5.6: sem parâmetros, o endpoint devolve no máximo 50 registros."""
    total = _seed_57(db_session)
    assert total == 57

    resp = api_client.get("/v1/cub/latest")
    assert resp.status_code == 200
    assert len(resp.json()) == 50  # RED: hoje devolve as 57 (sem paginação)


def test_latest_limit_explicito(api_client, db_session):
    """§5.6: `limit` é personalizável na consulta."""
    _seed_57(db_session)

    resp = api_client.get("/v1/cub/latest?limit=7")
    assert resp.status_code == 200
    assert len(resp.json()) == 7  # RED: hoje o parâmetro é ignorado


def test_latest_limit_zero_ilimitado(api_client, db_session):
    """§5.6: `limit=0` = sem limite (payload completo sob demanda)."""
    _seed_57(db_session)

    resp = api_client.get("/v1/cub/latest?limit=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 57


def test_latest_limit_negativo_rejeitado(api_client, db_session):
    """§5.6: `limit` negativo é inválido (422), não silencioso."""
    _seed_57(db_session)

    resp = api_client.get("/v1/cub/latest?limit=-1")
    assert resp.status_code == 422  # RED: hoje é ignorado (200)
