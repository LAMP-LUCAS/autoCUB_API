from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict
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
    ComparativoItem,
    PanoramaResponse,
    PanoramaMetricas,
    PanoramaEstruturaAgrupada,
    BlocoPadroes,
    ProjetoDestaque,
    ImpactoDesoneracaoResponse,
    ItemImpactoDesoneracao,
    RankingResponse,
    RankingItem
)

router = APIRouter(prefix="/cub", tags=["CUB / Custo Unitário Básico"])


# ==============================================================================
# 1. COTAÇÕES MAIS RECENTES (Com Origem Completa: UF, Sinduscon e Região)
# ==============================================================================

@router.get("/latest", response_model=List[CubCotacaoResponse], summary="Últimas cotações CUB com origem completa")
def get_latest_cub(
    uf: Optional[str] = Query(None, description="Filtrar por UF específica (ex: GO, MG, PR). Se omitido, lista todas."),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    db: Session = Depends(get_db)
):
    """
    Retorna as cotações mais recentes disponíveis na base de dados, garantindo que
    cada item contenha explicitamente sua ORIGEM COMPLETA (UF, Sinduscon e Região).
    """
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

    # Subquery para identificar a data mais recente de cada sinduscon e padrão
    subq_filter = (CubMensal.desoneracao == deson_slug)
    if uf:
        subq_filter = subq_filter & (Sinduscon.uf == uf.upper())

    subq = (
        db.query(
            CubMensal.sinduscon_id,
            CubMensal.codigo_padrao,
            func.max(CubMensal.data_referencia).label("max_data")
        )
        .join(Sinduscon, CubMensal.sinduscon_id == Sinduscon.id)
        .filter(subq_filter)
        .group_by(CubMensal.sinduscon_id, CubMensal.codigo_padrao)
        .subquery()
    )

    query = (
        db.query(CubMensal, Sinduscon, PadraoProjeto)
        .join(
            subq,
            (CubMensal.sinduscon_id == subq.c.sinduscon_id) &
            (CubMensal.codigo_padrao == subq.c.codigo_padrao) &
            (CubMensal.data_referencia == subq.c.max_data)
        )
        .join(Sinduscon, CubMensal.sinduscon_id == Sinduscon.id)
        .outerjoin(PadraoProjeto, CubMensal.codigo_padrao == PadraoProjeto.codigo)
        .filter(CubMensal.desoneracao == deson_slug)
    )

    results = query.order_by(Sinduscon.uf, CubMensal.codigo_padrao).all()

    response = []
    for cub, sind, padrao in results:
        response.append(
            CubCotacaoResponse(
                uf=sind.uf,
                sinduscon_id=sind.id,
                sinduscon_nome=sind.nome,
                regiao=sind.regiao,
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


# ==============================================================================
# 2. PANORAMA ESTRUTURADO & ANÁLISES PRÉ-CALCULADAS (Estilo autoSINAPI / BI)
# ==============================================================================

@router.get("/{uf}/panorama", response_model=PanoramaResponse, summary="Panorama completo estruturado e métricas pré-calculadas")
def get_cub_panorama(
    uf: str,
    ano: Optional[int] = Query(None, description="Ano de referência (padrão: mais recente)"),
    mes: Optional[int] = Query(None, description="Mês de referência (padrão: mais recente)"),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon específico"),
    db: Session = Depends(get_db)
):
    """
    Retorna a visualização analítica completa e estruturada da NBR 12.721 para uma UF:
    - Métricas executivas pré-calculadas (médias setoriais, maior/menor custo, maiores oscilações);
    - Estrutura agrupada hierarquicamente por Categoria (Residencial, Comercial, Especial)
      e por Padrão de Acabamento (Baixo, Normal, Alto) com médias parciais.
    """
    uf_upper = uf.upper()
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

    # Identifica data alvo
    if ano and mes:
        target_date = date(ano, mes, 1)
    else:
        target_date = (
            db.query(func.max(CubMensal.data_referencia))
            .filter(CubMensal.sinduscon_id == sind.id, CubMensal.desoneracao == deson_slug)
            .scalar()
        )
        if not target_date:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum dado encontrado para a UF '{uf_upper}' na série '{deson_slug}'."
            )

    rows = (
        db.query(CubMensal, PadraoProjeto)
        .outerjoin(PadraoProjeto, CubMensal.codigo_padrao == PadraoProjeto.codigo)
        .filter(
            CubMensal.sinduscon_id == sind.id,
            CubMensal.data_referencia == target_date,
            CubMensal.desoneracao == deson_slug
        )
        .order_by(CubMensal.codigo_padrao)
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sem cotações para {uf_upper} na data {target_date}."
        )

    cotacoes_dto: List[CubCotacaoResponse] = []
    valores_todos: List[Decimal] = []
    valores_res: List[Decimal] = []
    valores_com: List[Decimal] = []
    valores_esp: List[Decimal] = []

    # Destaques
    maior_custo_item = None
    menor_custo_item = None
    maior_alta_item = None
    maior_queda_item = None

    # Estrutura agrupada
    arvore = {
        "residencial": {"baixo": [], "normal": [], "alto": []},
        "comercial": {"normal": [], "alto": []},
        "especial": {"unico": []}
    }

    for cub, padrao in rows:
        val = cub.valor_m2
        valores_todos.append(val)
        cat = (padrao.categoria if padrao else "OUTROS").upper()
        acab = (padrao.padrao_acabamento if padrao else "NORMAL").lower()
        nome = padrao.nome if padrao else cub.codigo_padrao

        dto = CubCotacaoResponse(
            uf=sind.uf,
            sinduscon_id=sind.id,
            sinduscon_nome=sind.nome,
            regiao=sind.regiao,
            codigo_padrao=cub.codigo_padrao,
            padrao_nome=nome,
            categoria=cat,
            padrao_acabamento=acab.upper(),
            valor_m2=val,
            variacao_mensal_pct=cub.variacao_mensal_pct,
            desoneracao=cub.desoneracao,
            data_referencia=cub.data_referencia
        )
        cotacoes_dto.append(dto)

        # Agrupamento
        if cat == "RESIDENCIAL":
            valores_res.append(val)
            if acab in arvore["residencial"]:
                arvore["residencial"][acab].append(dto)
        elif cat == "COMERCIAL":
            valores_com.append(val)
            if acab in arvore["comercial"]:
                arvore["comercial"][acab].append(dto)
        elif cat == "ESPECIAL":
            valores_esp.append(val)
            arvore["especial"]["unico"].append(dto)

        # Maior / Menor Custo
        if maior_custo_item is None or val > maior_custo_item.valor_m2:
            maior_custo_item = ProjetoDestaque(codigo=cub.codigo_padrao, nome=nome, valor_m2=val)
        if menor_custo_item is None or val < menor_custo_item.valor_m2:
            menor_custo_item = ProjetoDestaque(codigo=cub.codigo_padrao, nome=nome, valor_m2=val)

        # Oscilações mensais
        if cub.variacao_mensal_pct is not None:
            if maior_alta_item is None or cub.variacao_mensal_pct > maior_alta_item.variacao_pct:
                maior_alta_item = ProjetoDestaque(
                    codigo=cub.codigo_padrao, nome=nome, valor_m2=val, variacao_pct=cub.variacao_mensal_pct
                )
            if maior_queda_item is None or cub.variacao_mensal_pct < maior_queda_item.variacao_pct:
                maior_queda_item = ProjetoDestaque(
                    codigo=cub.codigo_padrao, nome=nome, valor_m2=val, variacao_pct=cub.variacao_mensal_pct
                )

    def calc_media(lst: List[Decimal]) -> Decimal:
        return round(sum(lst) / len(lst), 2) if lst else Decimal("0.00")

    def monta_bloco(lista: List[CubCotacaoResponse]) -> BlocoPadroes:
        vals = [p.valor_m2 for p in lista]
        return BlocoPadroes(
            total_projetos=len(lista),
            media_m2=calc_media(vals),
            projetos=lista
        )

    estrutura_agrupada = PanoramaEstruturaAgrupada(
        residencial={
            "baixo": monta_bloco(arvore["residencial"]["baixo"]),
            "normal": monta_bloco(arvore["residencial"]["normal"]),
            "alto": monta_bloco(arvore["residencial"]["alto"])
        },
        comercial={
            "normal": monta_bloco(arvore["comercial"]["normal"]),
            "alto": monta_bloco(arvore["comercial"]["alto"])
        },
        especial={
            "unico": monta_bloco(arvore["especial"]["unico"])
        }
    )

    metricas = PanoramaMetricas(
        media_geral_m2=calc_media(valores_todos),
        media_residencial_m2=calc_media(valores_res),
        media_comercial_m2=calc_media(valores_com),
        media_especial_m2=calc_media(valores_esp),
        maior_custo=maior_custo_item,
        menor_custo=menor_custo_item,
        maior_alta_mensal=maior_alta_item,
        maior_queda_mensal=maior_queda_item
    )

    return PanoramaResponse(
        uf=sind.uf,
        sinduscon_id=sind.id,
        sinduscon_nome=sind.nome,
        regiao=sind.regiao,
        data_referencia=target_date,
        desoneracao=deson_slug,
        total_projetos=len(cotacoes_dto),
        metricas=metricas,
        estrutura_agrupada=estrutura_agrupada
    )


# ==============================================================================
# 3. IMPACTO TRIBUTÁRIO DA DESONERAÇÃO (Cruzamento Pré-calculado)
# ==============================================================================

@router.get("/{uf}/impacto-desoneracao", response_model=ImpactoDesoneracaoResponse, summary="Impacto financeiro da desoneração da folha por m²")
def get_impacto_desoneracao(
    uf: str,
    ano: Optional[int] = Query(None, description="Ano de referência"),
    mes: Optional[int] = Query(None, description="Mês de referência"),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon"),
    db: Session = Depends(get_db)
):
    """
    Cruza em tempo recorde as séries 'SEM_DESONERACAO' e 'COM_DESONERACAO' para o mesmo período/UF,
    calculando a economia em R$/m² e a redução percentual proporcionada pela desoneração da folha.
    """
    uf_upper = uf.upper()
    sind = db.query(Sinduscon).filter(Sinduscon.uf == uf_upper, Sinduscon.ativo == True).first()
    if not sind:
        raise HTTPException(status_code=404, detail=f"Sinduscon não encontrado para {uf_upper}.")

    if ano and mes:
        target_date = date(ano, mes, 1)
    else:
        target_date = (
            db.query(func.max(CubMensal.data_referencia))
            .filter(CubMensal.sinduscon_id == sind.id)
            .scalar()
        )
        if not target_date:
            raise HTTPException(status_code=404, detail=f"Sem dados para {uf_upper}.")

    cotacoes_sem = {
        c.codigo_padrao: c
        for c in db.query(CubMensal).filter(
            CubMensal.sinduscon_id == sind.id,
            CubMensal.data_referencia == target_date,
            CubMensal.desoneracao == "SEM_DESONERACAO"
        ).all()
    }

    cotacoes_com = {
        c.codigo_padrao: c
        for c in db.query(CubMensal).filter(
            CubMensal.sinduscon_id == sind.id,
            CubMensal.data_referencia == target_date,
            CubMensal.desoneracao == "COM_DESONERACAO"
        ).all()
    }

    padroes = {p.codigo: p for p in db.query(PadraoProjeto).all()}

    itens: List[ItemImpactoDesoneracao] = []
    economias_reais = []
    economias_pct = []

    for codigo, c_sem in cotacoes_sem.items():
        c_com = cotacoes_com.get(codigo)
        if not c_com:
            continue

        padrao = padroes.get(codigo)
        diff = c_sem.valor_m2 - c_com.valor_m2
        pct = round((diff / c_sem.valor_m2) * 100, 2) if c_sem.valor_m2 > 0 else Decimal("0.00")

        economias_reais.append(diff)
        economias_pct.append(pct)

        itens.append(
            ItemImpactoDesoneracao(
                codigo_padrao=codigo,
                padrao_nome=padrao.nome if padrao else codigo,
                categoria=padrao.categoria if padrao else "OUTROS",
                padrao_acabamento=padrao.padrao_acabamento if padrao else "UNICO",
                valor_sem_desoneracao=c_sem.valor_m2,
                valor_com_desoneracao=c_com.valor_m2,
                economia_reais_m2=round(diff, 2),
                economia_percentual=pct
            )
        )

    itens.sort(key=lambda x: x.economia_reais_m2, reverse=True)

    media_reais = round(sum(economias_reais) / len(economias_reais), 2) if economias_reais else Decimal("0.00")
    media_pct = round(sum(economias_pct) / len(economias_pct), 2) if economias_pct else Decimal("0.00")

    return ImpactoDesoneracaoResponse(
        uf=sind.uf,
        sinduscon_id=sind.id,
        sinduscon_nome=sind.nome,
        data_referencia=target_date,
        economia_media_reais_m2=media_reais,
        economia_media_percentual=media_pct,
        projetos=itens
    )


# ==============================================================================
# 4. RANKING NACIONAL PRÉ-CALCULADO
# ==============================================================================

@router.get("/ranking", response_model=RankingResponse, summary="Ranking de custos entre estados com desvio da média")
def get_cub_ranking(
    codigo_padrao: str = Query("R1-N", description="Código do padrão (ex: R1-N, R8-N, GI)"),
    ano: Optional[int] = Query(None, description="Ano"),
    mes: Optional[int] = Query(None, description="Mês"),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    db: Session = Depends(get_db)
):
    """
    Classifica todos os estados da base por ordem de custo do m² para um padrão construtivo,
    calculando a média nacional amostral e o desvio percentual de cada praça.
    """
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"
    codigo_padrao_norm = codigo_padrao.upper()

    padrao = db.query(PadraoProjeto).filter(PadraoProjeto.codigo == codigo_padrao_norm).first()
    padrao_nome = padrao.nome if padrao else codigo_padrao_norm

    if ano and mes:
        target_date = date(ano, mes, 1)
    else:
        target_date = (
            db.query(func.max(CubMensal.data_referencia))
            .filter(CubMensal.codigo_padrao == codigo_padrao_norm, CubMensal.desoneracao == deson_slug)
            .scalar()
        )
        if not target_date:
            raise HTTPException(status_code=404, detail=f"Sem dados para {codigo_padrao_norm}.")

    results = (
        db.query(CubMensal, Sinduscon)
        .join(Sinduscon, CubMensal.sinduscon_id == Sinduscon.id)
        .filter(
            CubMensal.codigo_padrao == codigo_padrao_norm,
            CubMensal.data_referencia == target_date,
            CubMensal.desoneracao == deson_slug
        )
        .order_by(desc(CubMensal.valor_m2))
        .all()
    )

    if not results:
        raise HTTPException(status_code=404, detail=f"Nenhum dado encontrado para {codigo_padrao_norm} na data {target_date}.")

    valores = [c.valor_m2 for c, s in results]
    media_nac = round(sum(valores) / len(valores), 2)

    ranking_items = []
    for idx, (cub, sind) in enumerate(results, start=1):
        desvio = round(((cub.valor_m2 - media_nac) / media_nac) * 100, 2)
        ranking_items.append(
            RankingItem(
                posicao=idx,
                uf=sind.uf,
                sinduscon_nome=sind.nome,
                regiao=sind.regiao,
                valor_m2=cub.valor_m2,
                variacao_mensal_pct=cub.variacao_mensal_pct,
                desvio_media_pct=desvio
            )
        )

    return RankingResponse(
        codigo_padrao=codigo_padrao_norm,
        padrao_nome=padrao_nome,
        data_referencia=target_date,
        desoneracao=deson_slug,
        total_estados=len(ranking_items),
        media_nacional=media_nac,
        ranking=ranking_items
    )


# ==============================================================================
# 5. SÉRIE HISTÓRICA ENRIQUECIDA COM INDICADORES ACUMULADOS
# ==============================================================================

@router.get("/{uf}/historico/{codigo_padrao}", response_model=CubHistoricoResponse, summary="Série histórica com inflação acumulada e estatísticas")
def get_historico_padrao(
    uf: str,
    codigo_padrao: str,
    ano_inicio: Optional[int] = Query(None, description="Ano inicial"),
    ano_fim: Optional[int] = Query(None, description="Ano final"),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon"),
    db: Session = Depends(get_db)
):
    """
    Retorna a série histórica com métricas consolidadas pré-calculadas:
    - Variação acumulada no período selecionado (inflação setorial acumulada);
    - Variação média mensal;
    - Menor e maior cotação do período;
    - Variação acumulada mês a mês.
    """
    uf_upper = uf.upper()
    codigo_padrao_norm = codigo_padrao.upper()
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

    sind_query = db.query(Sinduscon).filter(Sinduscon.uf == uf_upper, Sinduscon.ativo == True)
    if sinduscon_id:
        sind_query = sind_query.filter(Sinduscon.id == sinduscon_id)

    sind = sind_query.first()
    if not sind:
        raise HTTPException(status_code=404, detail=f"Sinduscon não encontrado para {uf_upper}.")

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

    if not registros:
        raise HTTPException(status_code=404, detail=f"Nenhum registro histórico para {uf_upper} e padrão {codigo_padrao_norm}.")

    val_inicial = registros[0].valor_m2
    val_final = registros[-1].valor_m2
    var_acumulada_total = round(((val_final - val_inicial) / val_inicial) * 100, 2) if val_inicial > 0 else Decimal("0.00")

    valores = [r.valor_m2 for r in registros]
    vars_mensais = [r.variacao_mensal_pct for r in registros if r.variacao_mensal_pct is not None]
    var_media_mensal = round(sum(vars_mensais) / len(vars_mensais), 2) if vars_mensais else Decimal("0.00")

    serie = []
    for r in registros:
        var_acum_mes = round(((r.valor_m2 - val_inicial) / val_inicial) * 100, 2) if val_inicial > 0 else Decimal("0.00")
        serie.append(
            CubHistoricoItem(
                data_referencia=r.data_referencia,
                valor_m2=r.valor_m2,
                variacao_mensal_pct=r.variacao_mensal_pct,
                variacao_acumulada_pct=var_acum_mes
            )
        )

    return CubHistoricoResponse(
        uf=sind.uf,
        sinduscon_id=sind.id,
        sinduscon_nome=sind.nome,
        codigo_padrao=codigo_padrao_norm,
        padrao_nome=padrao_nome,
        desoneracao=deson_slug,
        total_meses=len(serie),
        valor_inicial=val_inicial,
        valor_final=val_final,
        variacao_acumulada_periodo_pct=var_acumulada_total,
        variacao_media_mensal_pct=var_media_mensal,
        menor_valor_m2=min(valores),
        maior_valor_m2=max(valores),
        serie_historica=serie
    )


# ==============================================================================
# 6. CONSULTA BÁSICA POR UF & COMPARATIVO
# ==============================================================================

@router.get("/comparativo", response_model=ComparativoResponse, summary="Comparativo regional de CUB entre estados")
def get_comparativo_regional(
    ufs: str = Query(..., description="Lista de UFs separadas por vírgula (ex: GO,MG,PR,RJ)"),
    codigo_padrao: str = Query("R1-N", description="Código canônico NBR (ex: R1-N, R8-N, CSL-8-N)"),
    ano: Optional[int] = Query(None, description="Ano"),
    mes: Optional[int] = Query(None, description="Mês"),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    db: Session = Depends(get_db)
):
    """Compara o custo do m² entre múltiplos estados no mesmo período."""
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
        latest_date = (
            db.query(func.max(CubMensal.data_referencia))
            .filter(CubMensal.codigo_padrao == codigo_padrao_norm, CubMensal.desoneracao == deson_slug)
            .scalar()
        )
        if not latest_date:
            raise HTTPException(status_code=404, detail=f"Sem dados para {codigo_padrao_norm}.")
        data_ref = latest_date
        query = query.filter(CubMensal.data_referencia == data_ref)

    results = query.all()
    items = [
        ComparativoItem(
            uf=sind.uf,
            sinduscon_nome=sind.nome,
            regiao=sind.regiao,
            valor_m2=cub.valor_m2,
            variacao_mensal_pct=cub.variacao_mensal_pct
        )
        for cub, sind in results
    ]

    valores = [i.valor_m2 for i in items]
    media_grp = round(sum(valores) / len(valores), 2) if valores else Decimal("0.00")

    return ComparativoResponse(
        codigo_padrao=codigo_padrao_norm,
        padrao_nome=padrao_nome,
        data_referencia=data_ref,
        desoneracao=deson_slug,
        total_comparados=len(items),
        media_grupo=media_grp,
        comparativo=items
    )


@router.get("/{uf}", response_model=List[CubEstadoPeriodoResponse], summary="Consulta cotações do CUB por estado")
def get_cub_by_uf(
    uf: str,
    ano: Optional[int] = Query(None, description="Ano"),
    mes: Optional[int] = Query(None, description="Mês"),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'"),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon"),
    db: Session = Depends(get_db)
):
    """Retorna as cotações de todos os projetos para uma determinada UF no mês/ano indicado."""
    uf_upper = uf.upper()
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

    sinds_query = db.query(Sinduscon).filter(Sinduscon.uf == uf_upper, Sinduscon.ativo == True)
    if sinduscon_id:
        sinds_query = sinds_query.filter(Sinduscon.id == sinduscon_id)

    sinduscons = sinds_query.all()
    if not sinduscons:
        raise HTTPException(status_code=404, detail=f"Nenhum Sinduscon para {uf_upper}.")

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
            cotacoes_dto = [
                CubCotacaoResponse(
                    uf=sind.uf,
                    sinduscon_id=sind.id,
                    sinduscon_nome=sind.nome,
                    regiao=sind.regiao,
                    codigo_padrao=cub.codigo_padrao,
                    padrao_nome=padrao.nome if padrao else cub.codigo_padrao,
                    categoria=padrao.categoria if padrao else None,
                    padrao_acabamento=padrao.padrao_acabamento if padrao else None,
                    valor_m2=cub.valor_m2,
                    variacao_mensal_pct=cub.variacao_mensal_pct,
                    desoneracao=cub.desoneracao,
                    data_referencia=cub.data_referencia
                )
                for cub, padrao in cotacoes_raw
            ]

            response_list.append(
                CubEstadoPeriodoResponse(
                    uf=sind.uf,
                    sinduscon_id=sind.id,
                    sinduscon_nome=sind.nome,
                    regiao=sind.regiao,
                    data_referencia=ref_date,
                    desoneracao=deson_slug,
                    total_projetos=len(cotacoes_dto),
                    cotacoes=cotacoes_dto
                )
            )

    return response_list
