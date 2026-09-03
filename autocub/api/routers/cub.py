from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from autocub.database.connection import get_db
from autocub.database.models import CubMensal, Sinduscon, PadraoProjeto
from autocub.processor.schemas import (
    CubCotacaoResponse,
    CubEstadoPeriodoResponse,
    CubHistoricoResponse,
    CubHistoricoItem,
    ComparativoResponse,
    ComparativoItem
)

router = APIRouter(prefix="/cub", tags=["CUB / Custo Unitário Básico"])


@router.get("/latest", response_model=List[CubCotacaoResponse], summary="Últimas cotações CUB disponíveis")
def get_latest_cub(
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    db: Session = Depends(get_db)
):
    """
    Retorna a cotação mais recente cadastrada para os projetos-padrão em cada Sinduscon.
    """
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

    # Subquery para encontrar a data mais recente por sinduscon e padrão
    subq = (
        db.query(
            CubMensal.sinduscon_id,
            CubMensal.codigo_padrao,
            func.max(CubMensal.data_referencia).label("max_data")
        )
        .filter(CubMensal.desoneracao == deson_slug)
        .group_by(CubMensal.sinduscon_id, CubMensal.codigo_padrao)
        .subquery()
    )

    results = (
        db.query(CubMensal, PadraoProjeto)
        .join(
            subq,
            (CubMensal.sinduscon_id == subq.c.sinduscon_id) &
            (CubMensal.codigo_padrao == subq.c.codigo_padrao) &
            (CubMensal.data_referencia == subq.c.max_data)
        )
        .outerjoin(PadraoProjeto, CubMensal.codigo_padrao == PadraoProjeto.codigo)
        .filter(CubMensal.desoneracao == deson_slug)
        .all()
    )

    response = []
    for cub, padrao in results:
        response.append(
            CubCotacaoResponse(
                codigo_padrao=cub.codigo_padrao,
                padrao_nome=padrao.nome if padrao else cub.codigo_padrao,
                categoria=padrao.categoria if padrao else None,
                padrao_acabamento=padrao.padrao_acabamento if padrao else None,
                valor_m2=cub.valor_m2,
                variacao_mensal_pct=cub.variacao_mensal_pct,
                desoneracao=cub.desoneracao,
                data_referencia=cub.data_referencia
            )
        )
    return response


@router.get("/comparativo", response_model=ComparativoResponse, summary="Comparativo regional de CUB entre estados")
def get_comparativo_regional(
    ufs: str = Query(..., description="Lista de UFs separadas por vírgula (ex: GO,MG,PR,RJ)"),
    codigo_padrao: str = Query("R1-N", description="Código canônico NBR (ex: R1-N, R8-N, CSL-8-N)"),
    ano: Optional[int] = Query(None, description="Ano da cotação (padrão: ano mais recente)"),
    mes: Optional[int] = Query(None, description="Mês da cotação (padrão: mês mais recente)"),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    db: Session = Depends(get_db)
):
    """
    Permite comparar o custo por metro quadrado (R$/m²) de um determinado padrão construtivo
    entre diferentes estados ou regiões do Brasil no mesmo período.
    """
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"
    codigo_padrao_norm = codigo_padrao.upper()

    padrao = db.query(PadraoProjeto).filter(PadraoProjeto.codigo == codigo_padrao_norm).first()
    padrao_nome = padrao.nome if padrao else codigo_padrao_norm

    lista_ufs = [u.strip().upper() for u in ufs.split(",") if u.strip()]

    query = (
        db.query(CubMensal, Sinduscon)
        .join(Sinduscon, CubMensal.sinduscon_id == Sinduscon.id)
        .filter(
            Sinduscon.uf.in_(lista_ufs),
            CubMensal.codigo_padrao == codigo_padrao_norm,
            CubMensal.desoneracao == deson_slug
        )
    )

    if ano and mes:
        data_ref = date(ano, mes, 1)
        query = query.filter(CubMensal.data_referencia == data_ref)
    else:
        # Pega a data mais recente disponível na base
        latest_date = (
            db.query(func.max(CubMensal.data_referencia))
            .filter(CubMensal.codigo_padrao == codigo_padrao_norm, CubMensal.desoneracao == deson_slug)
            .scalar()
        )
        if not latest_date:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum dado encontrado para o padrão {codigo_padrao_norm}."
            )
        data_ref = latest_date
        query = query.filter(CubMensal.data_referencia == data_ref)

    results = query.all()

    items = []
    for cub, sind in results:
        items.append(
            ComparativoItem(
                uf=sind.uf,
                sinduscon_nome=sind.nome,
                valor_m2=cub.valor_m2,
                variacao_mensal_pct=cub.variacao_mensal_pct
            )
        )

    return ComparativoResponse(
        codigo_padrao=codigo_padrao_norm,
        padrao_nome=padrao_nome,
        data_referencia=data_ref,
        desoneracao=deson_slug,
        comparativo=items
    )


@router.get("/{uf}", response_model=List[CubEstadoPeriodoResponse], summary="Consulta cotações do CUB por estado")
def get_cub_by_uf(
    uf: str,
    ano: Optional[int] = Query(None, description="Ano de referência (ex: 2026)"),
    mes: Optional[int] = Query(None, description="Mês de referência (1 a 12)"),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon específico"),
    db: Session = Depends(get_db)
):
    """
    Retorna as cotações de todos os projetos-padrão para uma determinada UF no mês/ano indicado.
    """
    uf_upper = uf.upper()
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

    sinds_query = db.query(Sinduscon).filter(Sinduscon.uf == uf_upper, Sinduscon.ativo == True)
    if sinduscon_id:
        sinds_query = sinds_query.filter(Sinduscon.id == sinduscon_id)

    sinduscons = sinds_query.all()
    if not sinduscons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum Sinduscon ativo encontrado para a UF '{uf_upper}'."
        )

    response_list = []

    for sind in sinduscons:
        query = (
            db.query(CubMensal, PadraoProjeto)
            .outerjoin(PadraoProjeto, CubMensal.codigo_padrao == PadraoProjeto.codigo)
            .filter(
                CubMensal.sinduscon_id == sind.id,
                CubMensal.desoneracao == deson_slug
            )
        )

        if ano and mes:
            target_date = date(ano, mes, 1)
            query = query.filter(CubMensal.data_referencia == target_date)
        elif ano:
            query = query.filter(func.extract("year", CubMensal.data_referencia) == ano)
        else:
            # Pega o mês mais recente disponível para este sinduscon
            max_dt = (
                db.query(func.max(CubMensal.data_referencia))
                .filter(CubMensal.sinduscon_id == sind.id, CubMensal.desoneracao == deson_slug)
                .scalar()
            )
            if max_dt:
                query = query.filter(CubMensal.data_referencia == max_dt)

        cotacoes_raw = query.order_by(CubMensal.data_referencia.desc(), CubMensal.codigo_padrao).all()

        if cotacoes_raw:
            ref_date = cotacoes_raw[0][0].data_referencia
            cotacoes_dto = []
            for cub, padrao in cotacoes_raw:
                cotacoes_dto.append(
                    CubCotacaoResponse(
                        codigo_padrao=cub.codigo_padrao,
                        padrao_nome=padrao.nome if padrao else cub.codigo_padrao,
                        categoria=padrao.categoria if padrao else None,
                        padrao_acabamento=padrao.padrao_acabamento if padrao else None,
                        valor_m2=cub.valor_m2,
                        variacao_mensal_pct=cub.variacao_mensal_pct,
                        desoneracao=cub.desoneracao,
                        data_referencia=cub.data_referencia
                    )
                )

            response_list.append(
                CubEstadoPeriodoResponse(
                    uf=sind.uf,
                    sinduscon_id=sind.id,
                    sinduscon_nome=sind.nome,
                    data_referencia=ref_date,
                    desoneracao=deson_slug,
                    total_projetos=len(cotacoes_dto),
                    cotacoes=cotacoes_dto
                )
            )

    return response_list


@router.get("/{uf}/historico/{codigo_padrao}", response_model=CubHistoricoResponse, summary="Série histórica de um padrão em um estado")
def get_historico_padrao(
    uf: str,
    codigo_padrao: str,
    ano_inicio: Optional[int] = Query(None, description="Ano inicial do histórico"),
    ano_fim: Optional[int] = Query(None, description="Ano final do histórico"),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon específico"),
    db: Session = Depends(get_db)
):
    """
    Retorna a série temporal histórica completa de cotação mensal e variação percentual
    de um projeto-padrão específico (ex: R1-N, PP-4-B, GI) em uma UF.
    """
    uf_upper = uf.upper()
    codigo_padrao_norm = codigo_padrao.upper()
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

    sind_query = db.query(Sinduscon).filter(Sinduscon.uf == uf_upper, Sinduscon.ativo == True)
    if sinduscon_id:
        sind_query = sind_query.filter(Sinduscon.id == sinduscon_id)

    sind = sind_query.first()
    if not sind:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sinduscon não encontrado para a UF '{uf_upper}'."
        )

    padrao = db.query(PadraoProjeto).filter(PadraoProjeto.codigo == codigo_padrao_norm).first()
    padrao_nome = padrao.nome if padrao else codigo_padrao_norm

    query = (
        db.query(CubMensal)
        .filter(
            CubMensal.sinduscon_id == sind.id,
            CubMensal.codigo_padrao == codigo_padrao_norm,
            CubMensal.desoneracao == deson_slug
        )
    )

    if ano_inicio:
        query = query.filter(func.extract("year", CubMensal.data_referencia) >= ano_inicio)
    if ano_fim:
        query = query.filter(func.extract("year", CubMensal.data_referencia) <= ano_fim)

    registros = query.order_by(CubMensal.data_referencia.asc()).all()

    serie = [
        CubHistoricoItem(
            data_referencia=r.data_referencia,
            valor_m2=r.valor_m2,
            variacao_mensal_pct=r.variacao_mensal_pct
        )
        for r in registros
    ]

    return CubHistoricoResponse(
        uf=sind.uf,
        sinduscon_nome=sind.nome,
        codigo_padrao=codigo_padrao_norm,
        padrao_nome=padrao_nome,
        desoneracao=deson_slug,
        total_meses=len(serie),
        serie_historica=serie
    )
