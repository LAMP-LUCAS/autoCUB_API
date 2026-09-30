"""RED §Fase-5 (obs. pós-§5.1) — suíte nunca grava no Redis de produção.

A suíte roda dentro do container com `REDIS_HOST=autocub-redis` (DB0), o
Redis de produção: os endpoints com cache gravavam `cub:*` no DB0 durante os
testes (observação registrada no plano do repositório). Isolamento obrigatório:
a suíte deve apontar para um DB de teste (REDIS_DB != 0) ANTES de qualquer
import de `autocub.*`.
"""

from autocub.core.config import settings


def test_suite_usa_redis_isolado_nunca_db0():
    assert settings.REDIS_DB != 0, (
        "suíte grava no Redis de produção (DB0) — conftest.py deve forçar "
        "REDIS_DB de teste antes de importar autocub.*"
    )
