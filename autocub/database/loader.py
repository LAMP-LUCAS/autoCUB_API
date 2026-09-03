from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from autocub.database.models import CubMensal, EtlExecucao
from autocub.core.logging import logger


def upsert_cub_records(db: Session, records: List[Dict[str, Any]]) -> int:
    """
    Insere ou atualiza registros de cotação CUB de forma idempotente.
    Usa ON CONFLICT DO UPDATE nativo para PostgreSQL com fallback para outros bancos.
    """
    if not records:
        return 0

    count = 0
    try:
        is_postgres = db.bind and db.bind.dialect.name == "postgresql"
    except Exception:
        is_postgres = False

    if is_postgres:
        for item in records:
            stmt = pg_insert(CubMensal).values(
                sinduscon_id=item["sinduscon_id"],
                data_referencia=item["data_referencia"],
                codigo_padrao=item["codigo_padrao"],
                desoneracao=item["desoneracao"],
                valor_m2=item["valor_m2"],
                variacao_mensal_pct=item["variacao_mensal_pct"],
                data_extracao=item.get("data_extracao")
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["sinduscon_id", "data_referencia", "codigo_padrao", "desoneracao"],
                set_={
                    "valor_m2": stmt.excluded.valor_m2,
                    "variacao_mensal_pct": stmt.excluded.variacao_mensal_pct,
                    "data_extracao": stmt.excluded.data_extracao
                }
            )
            db.execute(stmt)
            count += 1
    else:
        for item in records:
            existing = db.query(CubMensal).filter_by(
                sinduscon_id=item["sinduscon_id"],
                data_referencia=item["data_referencia"],
                codigo_padrao=item["codigo_padrao"],
                desoneracao=item["desoneracao"]
            ).first()
            if existing:
                existing.valor_m2 = item["valor_m2"]
                existing.variacao_mensal_pct = item["variacao_mensal_pct"]
            else:
                db.add(CubMensal(**item))
            count += 1

    db.commit()
    logger.info(f"Salvos/atualizados {count} registros na tabela cub_mensal.")
    return count


def log_etl_execution(
    db: Session,
    sinduscon_id: int,
    ano: int,
    mes: int,
    desoneracao: str,
    status: str,
    registros: int = 0,
    mensagem_erro: str = None,
    duracao_ms: int = None
) -> EtlExecucao:
    exec_log = EtlExecucao(
        sinduscon_id=sinduscon_id,
        ano=ano,
        mes=mes,
        desoneracao=desoneracao,
        status=status,
        registros_processados=registros,
        mensagem_erro=mensagem_erro,
        duracao_ms=duracao_ms
    )
    db.add(exec_log)
    db.commit()
    return exec_log
