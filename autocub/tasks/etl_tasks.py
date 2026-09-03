import time
from datetime import datetime, date
from typing import List, Optional
from autocub.core.logging import logger
from autocub.database.connection import SessionLocal
from autocub.database.models import Sinduscon
from autocub.database.loader import upsert_cub_records, log_etl_execution
from autocub.downloader.collector import CubCollector
from autocub.processor.parser import parse_cub_pdf
from autocub.tasks.celery_app import celery_app


def process_single_cub_report(
    sinduscon_id: int,
    uf: str,
    ano: int,
    mes: int,
    desoneracao_param: str = "sem-desoneracao",
    force_download: bool = False
) -> int:
    """
    Executa o ciclo completo para 1 relatório:
    Download/Cache -> Parse Determinístico -> Upsert no Banco -> Log de Auditoria
    """
    db = SessionLocal()
    start_time = time.time()
    collector = CubCollector()

    # Normalização de desoneração
    desoneracao_slug = "COM_DESONERACAO" if "com" in desoneracao_param.lower() else "SEM_DESONERACAO"
    param_web = "com-desoneracao" if desoneracao_slug == "COM_DESONERACAO" else "sem-desoneracao"

    try:
        pdf_path, is_cached = collector.collect_pdf(
            uf=uf,
            sinduscon_id=sinduscon_id,
            ano=ano,
            mes=mes,
            desoneracao=param_web,
            force_download=force_download
        )

        relatorio = parse_cub_pdf(
            source=str(pdf_path),
            uf=uf,
            sinduscon_id=sinduscon_id,
            desoneracao=desoneracao_slug,
            ano_fallback=ano,
            mes_fallback=mes
        )

        records = []
        for item in relatorio.itens:
            records.append({
                "sinduscon_id": sinduscon_id,
                "data_referencia": relatorio.data_referencia,
                "codigo_padrao": item.codigo_canonico,
                "desoneracao": desoneracao_slug,
                "valor_m2": item.valor_m2,
                "variacao_mensal_pct": item.variacao_pct,
                "data_extracao": datetime.utcnow()
            })

        count = upsert_cub_records(db, records)
        duracao_ms = int((time.time() - start_time) * 1000)

        status_str = "CACHE_LOCAL" if is_cached else "SUCESSO"
        log_etl_execution(
            db=db,
            sinduscon_id=sinduscon_id,
            ano=ano,
            mes=mes,
            desoneracao=desoneracao_slug,
            status=status_str,
            registros=count,
            duracao_ms=duracao_ms
        )

        logger.info(
            f"Relatório processado: {uf} Sinduscon={sinduscon_id} "
            f"({ano}-{mes:02d}) [{desoneracao_slug}] -> {count} registros salvos ({duracao_ms}ms)"
        )
        return count

    except Exception as e:
        duracao_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Erro processando CUB {uf}/{sinduscon_id} {ano}-{mes:02d}: {str(e)}")
        log_etl_execution(
            db=db,
            sinduscon_id=sinduscon_id,
            ano=ano,
            mes=mes,
            desoneracao=desoneracao_slug,
            status="FALHA",
            registros=0,
            mensagem_erro=str(e),
            duracao_ms=duracao_ms
        )
        return 0
    finally:
        db.close()


def run_etl_pipeline(
    ano_inicio: int,
    ano_fim: int,
    ufs: Optional[List[str]] = None,
    desoneracoes: Optional[List[str]] = None,
    force_download: bool = False
) -> dict:
    """
    Pipeline principal executado progressivamente:
    Ano mais recente para o mais antigo, mês 12 para mês 1.
    """
    db = SessionLocal()
    query = db.query(Sinduscon).filter(Sinduscon.ativo == True)
    if ufs:
        upper_ufs = [u.upper() for u in ufs]
        query = query.filter(Sinduscon.uf.in_(upper_ufs))

    sinduscons = query.all()
    db.close()

    if not sinduscons:
        logger.warning("Nenhum Sinduscon encontrado para os filtros informados.")
        return {"status": "vazio", "total_processado": 0}

    desoneracoes = desoneracoes or ["sem-desoneracao", "com-desoneracao"]

    ano_atual = datetime.now().year
    mes_atual = datetime.now().month

    total_registros = 0
    total_relatorios = 0

    logger.info(
        f"Iniciando ETL progressivo: Anos {ano_fim} -> {ano_inicio}, "
        f"Sinduscons={len(sinduscons)}, Desonerações={desoneracoes}"
    )

    for ano in range(ano_fim, ano_inicio - 1, -1):
        for mes in range(12, 0, -1):
            if ano == ano_atual and mes > mes_atual:
                continue

            for sind in sinduscons:
                for deson in desoneracoes:
                    count = process_single_cub_report(
                        sinduscon_id=sind.id,
                        uf=sind.uf,
                        ano=ano,
                        mes=mes,
                        desoneracao_param=deson,
                        force_download=force_download
                    )
                    if count > 0:
                        total_registros += count
                        total_relatorios += 1

    logger.info(f"ETL finalizado: {total_relatorios} relatórios processados, {total_registros} registros no banco.")
    return {
        "status": "concluido",
        "relatorios_processados": total_relatorios,
        "registros_salvos": total_registros
    }


def _dummy_task_wrapper(func):
    func.delay = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Celery não instalado neste ambiente."))
    return func

if celery_app:
    populate_cub_task = celery_app.task(name="autocub.populate_cub_task", bind=True)(
        lambda self, ano_inicio, ano_fim, ufs=None, desoneracoes=None, force_download=False: run_etl_pipeline(
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            ufs=ufs,
            desoneracoes=desoneracoes,
            force_download=force_download
        )
    )
else:
    @_dummy_task_wrapper
    def populate_cub_task(*args, **kwargs):
        return run_etl_pipeline(*args, **kwargs)



if __name__ == "__main__":
    # Teste / CLI direto
    import argparse
    parser = argparse.ArgumentParser(description="AutoCUB ETL Pipeline")
    parser.add_argument("--ano-inicio", type=int, default=2026)
    parser.add_argument("--ano-fim", type=int, default=2026)
    parser.add_argument("--uf", type=str, default="GO")
    args = parser.parse_args()

    run_etl_pipeline(
        ano_inicio=args.ano_inicio,
        ano_fim=args.ano_fim,
        ufs=[args.uf] if args.uf else None
    )
