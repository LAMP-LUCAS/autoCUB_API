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


@router.post(
    "/etl/trigger",
    response_model=EtlTriggerResponse,
    summary="Dispara o pipeline ETL progressivo e ético (Celery / Background)",
    description=(
        "**Dor que resolve:** Coletar manualmente relatórios em PDF de dezenas de sindicatos estaduais "
        "consome horas e gera falhas operacionais. Este endpoint aciona um coletor ético automatizado que "
        "respeita taxas de requisição com jitter, aplica cache em disco, descobre dinamicamente os IDs oficiais "
        "da CBIC e bloqueia tentativas inválidas para períodos futuros.\n\n"
        "**Comportamento:**\n"
        "- Em produção com Celery/Redis, enfileira a tarefa assíncrona imediatamente e retorna o `task_id`.\n"
        "- Em ambiente de desenvolvimento sem Celery, executa em segundo plano via `BackgroundTasks` do FastAPI.\n"
        "- Valida rigorosamente a faixa temporal (rejeita anos futuros e limita ao último mês publicado)."
    )
)
def trigger_etl(
    background_tasks: BackgroundTasks,
    ano_inicio: int = Query(2026, description="Ano inicial para coleta", examples=[2026]),
    ano_fim: int = Query(2026, description="Ano final para coleta", examples=[2026]),
    ufs: Optional[str] = Query(None, description="UFs separadas por vírgula (ex: GO,MG). Se omitido, processa todas as UFs ativas.", examples=["GO,MG,RJ"]),
    desoneracao: Optional[str] = Query("sem-desoneracao", description="'sem-desoneracao', 'com-desoneracao' ou 'ambas'", examples=["sem-desoneracao"]),
    force_download: bool = Query(False, description="Se True, ignora os PDFs em cache local e força novo download da CBIC"),
):
    """Dispara o processo assíncrono de coleta, parse e ingestão de relatórios CUB."""
    lista_ufs = [u.strip().upper() for u in ufs.split(",")] if ufs else None

    from autocub.core.temporal import sanitize_etl_range

    try:
        ano_inicio, ano_fim, max_mes = sanitize_etl_range(ano_inicio, ano_fim)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

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


@router.get(
    "/etl/logs",
    summary="Logs de auditoria forense das execuções do ETL",
    description=(
        "**Dor que resolve:** Falta de rastreabilidade sobre a integridade dos dados históricos. "
        "Permite diagnosticar com precisão milimétrica quais meses/UFs foram ingeridos com sucesso, "
        "quais utilizaram cache local em disco, quanto tempo cada download durou e quais sindicatos "
        "apresentaram falhas ou indisponibilidade na CBIC.\n\n"
        "**Retorno:** Lista de execuções auditadas com status (`SUCESSO`, `FALHA`, `CACHE_LOCAL`, `NAO_SUPORTADO_CBIC`), "
        "quantidade de registros salvos e mensagens de erro capturadas."
    )
)
def list_etl_logs(
    limit: int = Query(50, ge=1, le=500, description="Quantidade máxima de registros retornados", examples=[50]),
    status_filter: Optional[str] = Query(None, description="Filtrar por status: SUCESSO, FALHA, CACHE_LOCAL, NAO_SUPORTADO_CBIC", examples=["SUCESSO"]),
    db: Session = Depends(get_db)
):
    """Retorna os registros históricos de auditoria do ETL para monitoramento de saúde."""

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


@router.get(
    "/etl/report",
    summary="Relatório executivo consolidado de auditoria e telemetria do ETL",
    description=(
        "**Dor que resolve:** Visibilidade total e em tempo real sobre a saúde do pipeline de dados, "
        "conciliação de cotações no PostgreSQL, taxas de sucesso/cache/falha, categorização dos principais "
        "motivos de erro, ocupação física de disco (PDFs e banco) e consumo de hardware (CPU, RAM, Rede).\n\n"
        "**Retorno:** Métricas consolidadas de eficiência, conciliação do banco, espaço em disco e telemetria de hardware."
    )
)
def get_etl_telemetry_report(
    db: Session = Depends(get_db)
):
    """Retorna o relatório consolidado de auditoria forense e telemetria do ETL."""
    from autocub.core.telemetry import generate_etl_audit_summary
    return generate_etl_audit_summary(db=db)

