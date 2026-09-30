"""LIM-38 — sinalização da limitação de cobertura de UF (auditoria MCP §5.0).

A auditoria classificou a cobertura 19/27 UFs como **limitação de roadmap,
não é defeito** (nem todos os estados fornecem CUB à CBIC; adapters de
outros ainda não implementados). Decisão do usuário (2026-09-30): **nota no
response** — responder com a nota ("dado ainda não disponibilizado pelo
CBIC; equipe de desenvolvimento procurando solução") em vez de erro 404
vazio ou `[]` vazio.

TDD: **sem RED** — por decisão, LIM-38 nunca gera teste vermelho (o claim
do gate `claim_lim38` cobre a *sinalização*, nunca a cobertura). Os testes
são escritos JUNTO com a implementação.

Superfícies cobertas:
- `/v1/cub/latest?uf=<sem adapter>` → envelope `{uf, items: [], nota_lim38}`
  (200, em vez de `[]`);
- 404 de cobertura ausente (`/v1/cub/SP`, `/v1/cub/SP/dash`,
  `/v1/cub/historico…`) → `detail` com a nota;
- guarda: UF coberta continua lista plana (contrato §5.6) e código
  inválido NÃO recebe a nota (não é cobertura, é erro comum).
"""
from datetime import date
from decimal import Decimal

from autocub.database.loader import upsert_cub_records
from autocub.database.models import PadraoProjeto

UF_SEM_ADAPTER = "SP"   # fora das 19 UFs cobertas (auditoria §5.0)
UF_COBERTA = "GO"       # Sinduscon-GO ativo no seed


def _assert_nota(texto: str) -> None:
    assert "CBIC" in texto, f"nota sem o emissor do dado: {texto!r}"
    assert "equipe" in texto, f"nota sem a equipe: {texto!r}"
    assert "solução" in texto, f"nota sem o encaminhamento: {texto!r}"
    assert "LIM-38" in texto, f"nota sem o marcador de roadmap: {texto!r}"


class TestLatestNotaLim38:
    def test_uf_sem_adapter_responde_envelope_com_nota(self, api_client):
        resp = api_client.get("/v1/cub/latest", params={"uf": UF_SEM_ADAPTER})
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, dict), (
            f"LIM-38: {UF_SEM_ADAPTER} devolveu lista (esperado envelope "
            f"com nota): {body!r}"
        )
        assert body["uf"] == UF_SEM_ADAPTER
        assert body["items"] == []
        _assert_nota(body["nota_lim38"])

    def test_uf_coberta_continua_lista_plana(self, api_client, db_session):
        """Guarda de contrato §5.6: envelope é SÓ o caso LIM-38 — a UF
        coberta (com ou sem dado) continua devolvendo a lista plana."""
        padroes = [p.codigo for p in db_session.query(PadraoProjeto).all()]
        upsert_cub_records(db_session, [{
            "sinduscon_id": 10,  # GO
            "data_referencia": date(2026, 8, 1),
            "codigo_padrao": cod,
            "desoneracao": "SEM_DESONERACAO",
            "valor_m2": Decimal("2400.00"),
            "variacao_mensal_pct": Decimal("0.4"),
        } for cod in padroes])

        resp = api_client.get("/v1/cub/latest", params={"uf": UF_COBERTA})
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list), (
            f"UF coberta virou envelope LIM-38: {body!r}"
        )
        assert body and all("nota_lim38" not in item for item in body)

    def test_uf_invalida_nao_recebe_a_nota(self, api_client):
        """Código que não é UF brasileira não é 'cobertura ausente' —
        a nota LIM-38 não pode marcar erro comum."""
        resp = api_client.get("/v1/cub/latest", params={"uf": "XX"})
        assert resp.status_code == 200
        body = resp.json()
        assert not (isinstance(body, dict) and "nota_lim38" in body), (
            f"código inválido recebeu a nota LIM-38: {body!r}"
        )


class Test404ComNotaLim38:
    def test_get_uf_sem_adapter_404_com_a_nota(self, api_client):
        resp = api_client.get(f"/v1/cub/{UF_SEM_ADAPTER}")
        assert resp.status_code == 404
        _assert_nota(resp.json()["detail"])

    def test_dash_sem_adapter_404_com_a_nota(self, api_client):
        resp = api_client.get(f"/v1/cub/{UF_SEM_ADAPTER}/dash")
        assert resp.status_code == 404
        _assert_nota(resp.json()["detail"])

    def test_404_de_codigo_invalido_sem_a_nota(self, api_client):
        resp = api_client.get("/v1/cub/XX")
        assert resp.status_code == 404
        assert "LIM-38" not in resp.json()["detail"], (
            "código inválido recebeu a nota LIM-38"
        )
