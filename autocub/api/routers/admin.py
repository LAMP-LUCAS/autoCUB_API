from typing import List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from autocub.database.connection import get_db
from autocub.database.models import EtlExecucao
from autocub.tasks.etl_tasks import populate_cub_task, run_etl_pipeline
from autocub.processor.schemas import EtlTriggerResponse
from autocub.core.logging import logger

router = APIRouter(prefix="/admin", tags=["Administração & ETL"])


@router.post("/etl/trigger", response_model=EtlTriggerResponse, summary="Dispara carga do pipeline ETL")
def trigger_etl(
    background_tasks: BackgroundTasks,
    ano_inicio: int = Query(2026, description="Ano inicial para coleta"),
    ano_fim: int = Query(2026, description="Ano final para coleta"),
    ufs: Optional[str] = Query(None, description="UFs separadas por vírgula (ex: GO,MG). Se vazio, processa todas."),
    desoneracao: Optional[str] = Query("sem-desoneracao", description="'sem-desoneracao', 'com-desoneracao' ou 'ambas'"),
    force_download: bool = Query(False, description="Ignora cache local e força novo download"),
):
    """
    Dispara o processo progressivo de download, extração e carga no banco de dados.
    Em produção com Celery/Redis, enfileira a tarefa assíncrona; em modo dev, roda em background task.
    """
    lista_ufs = [u.strip().upper() for u in ufs.split(",")] if ufs else None

    if desoneracao == "ambas":
        deson_list = ["sem-desoneracao", "com-desoneracao"]
    else:
        deson_list = [desoneracao]

    try:
        # Tenta disparar via Celery
        task = populate_cub_task.delay(
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            ufs=lista_ufs,
            desoneracoes=deson_list,
            force_download=force_download
        )
        task_id = str(task.id)
        msg = "Tarefa de ETL enfileirada no Celery com sucesso."
    except Exception as e:
        logger.warning(f"Celery indisponível ({str(e)}). Executando via BackgroundTasks do FastAPI.")
        import uuid
        task_id = f"local-{uuid.uuid4().hex[:8]}"
        background_tasks.add_task(
            run_etl_pipeline,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            ufs=lista_ufs,
            desoneracoes=deson_list,
            force_download=force_download
        )
        msg = "Tarefa de ETL iniciada em segundo plano na API."

    return EtlTriggerResponse(
        task_id=task_id,
        status="ENFILEIRADA",
        mensagem=msg
    )


@router.get("/etl/logs", summary="Logs de auditoria das execuções do ETL")
def list_etl_logs(
    limit: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = Query(None, description="Filtrar por SUCESSO, FALHA, CACHE_LOCAL"),
    db: Session = Depends(get_db)
):
    """
    Retorna os registros históricos de auditoria do ETL para monitoramento da saúde das coletas.
    """
    query = db.query(EtlExecucao)
    if status_filter:
        query = query.filter(EtlExecucao.status == status_filter.upper())

    logs = query.order_by(desc(EtlExecucao.created_at)).limit(limit).all()

    return [
        {
            "id": l.id,
            "sinduscon_id": l.sinduscon_id,
            "ano": l.ano,
            "mes": l.mes,
            "desoneracao": l.desoneracao,
            "status": l.status,
            "registros_processados": l.registros_processados,
            "mensagem_erro": l.mensagem_erro,
            "duracao_ms": l.duracao_ms,
            "created_at": l.created_at
        }
        for l in logs
    ]
