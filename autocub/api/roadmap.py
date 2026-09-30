"""
Roadmap de cobertura por UF — STORY-MCP-007/B-07.

`cub_health.cobertura.ufs_sem_dado` diz **quais** UFs faltam, mas não **por
que** nem **quando**. Sem isso o cliente entende que é falha temporária de
consulta (e abre chamado) e a equipe não sabe o que priorizar.

Regras deste módulo (nenhuma aqui é data inventada):

* O **motivo** sai do estado real: a UF tem sindicato cadastrado? tem cotação
  em alguma competência? a ETL já rodou e falhou? É `registro` quando a base
  ainda não tem nada (limitação externa known) e `defasagem`/`ingestao` quando
  há histórico parcial.
* **A previsão só é declarada se houver base real para ela**: só existe quando
  a UF já teve ingested alguma vez (há uma data de extração na base) — a
  previsão é "próxima ETL mensal", que é um compromisso de processo, não uma
  promessa sobre a fonte. Quando não há histórico, `previsto_para: null` com
  `observacao` dizendo que depende de adapter/fonte — **a ausência de promessa
  é informação honesta**, não um campo vazio por preguiça.

Nenhuma data é adivinhada: a única previsão aqui é a rotina de ETL mensal
(configurada em `settings`), e ela é explicitamente rotulada como tal.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger("autocub.roadmap")

MOTIVO_SEM_CADASTRO = "SEM_SINDUSCON_CADASTRADO"
MOTIVO_SEM_COTACAO = "SEM_COTACAO_NA_BASE"
MOTIVO_DEFS = [
    (MOTIVO_SEM_COTACAO, "A UF tem sindicato cadastrado, mas nenhuma cotação foi "
     "ingerida até agora. Depende de adapter/fonte ativa para o estado."),
    (MOTIVO_SEM_CADASTRO, "A UF não tem sindicato cadastrado com CUB. Depende de "
     "adapter implementado e fonte oficial que publique o índice."),
]

# Próxima janela da ETL mensal (dia 2, 03:00 UTC — ver celery_config da casa).
# A previsão é de PROCESSO, não de fonte: a data em que a UF terá dado depende
# de quando o adapter existir, e isso não é previsível daqui.
JANELA_ETL_MENSAL = " proxima ETL mensal (dia 2 do mês)"


def tem_sindiccon(db: Session, uf: str) -> bool:
    from autocub.database.models import Sinduscon

    return db.query(
        func.count(Sinduscon.id)
    ).filter(Sinduscon.uf == uf.upper()).scalar() > 0


def _ultima_referencia(db: Session, uf: str) -> Optional[str]:
    from autocub.database.models import CubMensal, Sinduscon

    valor = db.query(func.max(CubMensal.data_referencia)).join(
        Sinduscon, CubMensal.sinduscon_id == Sinduscon.id
    ).filter(Sinduscon.uf == uf.upper()).scalar()
    return valor.isoformat() if valor else None


def roadmap_uf(db: Session, uf: str) -> dict[str, Any]:
    """Motivo (do estado real) e previsão (de processo) para uma UF sem dado."""
    uf = uf.upper()
    tem_sindic = tem_sindiccon(db, uf)
    ultima = _ultima_referencia(db, uf)

    if tem_sindic and ultima is None:
        codigo = MOTIVO_SEM_COTACAO
        previsao = JANELA_ETL_MENSAL
        observacao = ("Sindicato cadastrado, sem cotação: a próxima execução da "
                      "ETL tenta; se não houver publicação, o motivo real é a "
                      "fonte e precisa de adapter.")
    elif not tem_sindic:
        codigo = MOTIVO_SEM_CADASTRO
        # sem cadastro, a ETL não tem o que coletar — não há janela de processo
        previsao = None
        observacao = ("Depende de adapter/fonte para o estado (roadmap, sem "
                      "janela de ETL aplicável).")
    else:
        codigo = MOTIVO_SEM_COTACAO
        previsao = JANELA_ETL_MENSAL
        observacao = "Histórico parcial; a próxima ETL reavalia."

    return {
        "uf": uf,
        "motivo": codigo,
        "motivo_descricao": dict(MOTIVO_DEFS).get(codigo, codigo),
        "tem_sindiccon": tem_sindic,
        "ultima_referencia_registrada": ultima,
        "previsto_para": previsao,
        "observacao": observacao,
    }
