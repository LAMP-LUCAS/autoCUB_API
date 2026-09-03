from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from autocub.database.connection import get_db
from autocub.database.models import CubMensal, Sinduscon, PadraoProjeto, PesoCubBrasil
from autocub.core.cache import cache_response
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
    RankingItem,
    CubBrasilResponse,
    CubBrasilItem
)

router = APIRouter(prefix="/cub", tags=["CUB / Custo Unitário Básico"])


# ==============================================================================
# 1. CUB BRASIL PONDERADO OFICIAL (CBIC / Quadro I e II)
# ==============================================================================

@router.get(
    "/br",
    response_model=CubBrasilResponse,
    summary="CUB Médio Brasil Oficial ponderado (21 capitais)",
    description=(
        "**Dor que resolve:** O Brasil não possui um custo único e direto da construção civil; a CBIC calcula "
        "o indicador oficial consolidado através da média ponderada representativa de 21 capitais (Quadros I e II). "
        "Fazer esse cálculo manualmente exige consultar e cruzar 21 planilhas estaduais com a tabela de pesos econômicos relativos.\n\n"
        "**Como funciona:** Aplica a fórmula oficial da CBIC: `CUB Brasil = ∑(Pi × Xi) / ∑Pi`, onde `Pi` é o peso econômico "
        "do Estado e `Xi` é a cotação do projeto-padrão representativo daquela praça.\n\n"
        "**Retorno:** CUB Médio Brasil oficial, soma dos pesos considerados, decomposição média por macrorregião geográfica "
        "e participação percentual efetiva de cada estado no índice nacional."
    )
)
@cache_response(ttl=86400, prefix="cub:br")
def get_cub_brasil(
    ano: Optional[int] = Query(None, description="Ano de referência (ex: 2026). Se omitido, utiliza o mês mais recente.", examples=[2026]),
    mes: Optional[int] = Query(None, description="Mês de referência (1 a 12). Se omitido, utiliza o mês mais recente.", examples=[8]),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'", examples=["SEM_DESONERACAO"]),
    db: Session = Depends(get_db)
):
    """Calcula o CUB Médio Brasil oficial por média ponderada das 21 capitais (Fórmula CBIC)."""

    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

    if ano and mes:
        target_date = date(ano, mes, 1)
    else:
        target_date = (
            db.query(func.max(CubMensal.data_referencia))
            .filter(CubMensal.desoneracao == deson_slug)
            .scalar()
        )
        if not target_date:
            raise HTTPException(status_code=404, detail="Nenhum dado cadastrado para cálculo do CUB Brasil.")

    pesos = db.query(PesoCubBrasil).all()
    if not pesos:
        raise HTTPException(status_code=404, detail="Tabela de ponderações do CUB Brasil vazia.")

    itens_brasil: List[CubBrasilItem] = []
    numerador_total = Decimal("0.00")
    denominador_total = Decimal("0.00")
    regioes_numerador: Dict[str, Decimal] = {}
    regioes_denominador: Dict[str, Decimal] = {}

    for p in pesos:
        sind = db.query(Sinduscon).filter(Sinduscon.uf == p.uf, Sinduscon.ativo == True).first()
        if not sind:
            continue

        cub = (
            db.query(CubMensal)
            .filter(
                CubMensal.sinduscon_id == sind.id,
                CubMensal.codigo_padrao == p.projeto_representativo,
                CubMensal.data_referencia == target_date,
                CubMensal.desoneracao == deson_slug
            )
            .first()
        )

        if not cub:
            # Fallback para R8-N ou qualquer padrão existente se o projeto representativo não foi coletado
            cub = (
                db.query(CubMensal)
                .filter(
                    CubMensal.sinduscon_id == sind.id,
                    CubMensal.data_referencia == target_date,
                    CubMensal.desoneracao == deson_slug
                )
                .first()
            )

        if cub:
            valor = cub.valor_m2
            peso = p.peso_relativo
            prod = valor * peso
            numerador_total += prod
            denominador_total += peso

            reg = p.regiao.upper()
            regioes_numerador[reg] = regioes_numerador.get(reg, Decimal("0.00")) + prod
            regioes_denominador[reg] = regioes_denominador.get(reg, Decimal("0.00")) + peso

            itens_brasil.append(
                CubBrasilItem(
                    uf=p.uf,
                    sinduscon_nome=p.sinduscon_nome,
                    regiao=p.regiao,
                    projeto_representativo=cub.codigo_padrao,
                    peso_relativo=peso,
                    valor_m2=valor,
                    participacao_efetiva_pct=Decimal("0.00")
                )
            )

    if denominador_total == 0:
        raise HTTPException(status_code=404, detail=f"Sem cotações suficientes para o período {target_date}.")

    cub_medio = round(numerador_total / denominador_total, 2)

    # Participação efetiva de cada estado no bolo
    for item in itens_brasil:
        item.participacao_efetiva_pct = round((item.peso_relativo / denominador_total) * 100, 2)

    por_regiao = {}
    for reg, num in regioes_numerador.items():
        den = regioes_denominador.get(reg, Decimal("1.00"))
        por_regiao[reg] = round(num / den, 2) if den > 0 else Decimal("0.00")

    return CubBrasilResponse(
        data_referencia=target_date,
        desoneracao=deson_slug,
        cub_medio_brasil=cub_medio,
        total_estados_ponderados=len(itens_brasil),
        soma_pesos=denominador_total,
        por_regiao=por_regiao,
        estados=itens_brasil
    )


# ==============================================================================
# 2. COTAÇÕES RECENTES COM ORIGEM COMPLETA
# ==============================================================================

@router.get(
    "/latest",
    response_model=List[CubCotacaoResponse],
    summary="Últimas cotações consolidadas com identificação de UF, Sinduscon e Região",
    description=(
        "**Dor que resolve:** Muitas APIs entregam valores soltos de CUB sem indicar claramente qual sindicato "
        "ou estado gerou aquele número, gerando ambiguidade e riscos contratuais. Este endpoint retorna as cotações "
        "mais recentes vigentes, garantindo rastreabilidade territorial completa (UF, ID e Nome do Sinduscon, Macrorregião).\n\n"
        "**Filtros:** Pode listar o panorama de todos os estados simultaneamente ou filtrar por uma UF específica."
    )
)
def get_latest_cub(
    uf: Optional[str] = Query(None, description="Filtrar por UF (ex: GO, MG, RJ). Se omitido, lista todas as UFs ativas.", examples=["GO"]),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'", examples=["SEM_DESONERACAO"]),
    db: Session = Depends(get_db)
):
    """Retorna cotações recentes contendo explicitamente UF, Sinduscon e Região de origem."""

    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

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

    return [
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
        for cub, sind, padrao in results
    ]


# ==============================================================================
# 3. PAINEL ANALÍTICO CONCISO /dash (com cache em memória Redis)
# ==============================================================================

@router.get(
    "/{uf}/dash",
    response_model=PanoramaResponse,
    summary="Painel analítico consolidado e agrupamentos NBR por categoria (cacheado)",
    description=(
        "**Dor que resolve:** Evita a sobrecarga de consultar dezenas de projetos individualmente para compreender "
        "o cenário de custos de um estado. Em uma única chamada ultrarrápida (servida em < 1ms via cache Redis), "
        "entrega médias por tipologia (Residencial, Comercial, Especial), os projetos de maior e menor custo e a "
        "árvore hierárquica por padrão de acabamento (Baixo, Normal, Alto).\n\n"
        "**Rota curta byte-saving:** Substitui a rota antiga mais verbosa `/panorama`."
    )
)
@router.get("/{uf}/panorama", response_model=PanoramaResponse, include_in_schema=False)
@cache_response(ttl=86400, prefix="cub:dash")
def get_cub_dash(
    uf: str,
    ano: Optional[int] = Query(None, description="Ano de referência (ex: 2026)", examples=[2026]),
    mes: Optional[int] = Query(None, description="Mês de referência (1 a 12)", examples=[8]),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'", examples=["SEM_DESONERACAO"]),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon específico (opcional para UFs multi-sindicatos como MG e PR)"),
    db: Session = Depends(get_db)
):
    """Retorna métricas consolidadas pré-calculadas e agrupamentos NBR da UF."""

    uf_upper = uf.upper()
    deson_slug = "COM_DESONERACAO" if "com" in desoneracao.lower() else "SEM_DESONERACAO"

    sind_query = db.query(Sinduscon).filter(Sinduscon.uf == uf_upper, Sinduscon.ativo == True)
    if sinduscon_id:
        sind_query = sind_query.filter(Sinduscon.id == sinduscon_id)

    sind = sind_query.first()
    if not sind:
        raise HTTPException(status_code=404, detail=f"Sinduscon não encontrado para a UF '{uf_upper}'.")

    if ano and mes:
        target_date = date(ano, mes, 1)
    else:
        target_date = (
            db.query(func.max(CubMensal.data_referencia))
            .filter(CubMensal.sinduscon_id == sind.id, CubMensal.desoneracao == deson_slug)
            .scalar()
        )
        if not target_date:
            raise HTTPException(status_code=404, detail=f"Sem cotações para {uf_upper}.")

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
        raise HTTPException(status_code=404, detail=f"Sem cotações para {uf_upper} na data {target_date}.")

    cotacoes_dto: List[CubCotacaoResponse] = []
    valores_todos: List[Decimal] = []
    valores_res: List[Decimal] = []
    valores_com: List[Decimal] = []
    valores_esp: List[Decimal] = []

    maior_custo_item = None
    menor_custo_item = None
    maior_alta_item = None
    maior_queda_item = None

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

        if maior_custo_item is None or val > maior_custo_item.valor_m2:
            maior_custo_item = ProjetoDestaque(codigo=cub.codigo_padrao, nome=nome, valor_m2=val)
        if menor_custo_item is None or val < menor_custo_item.valor_m2:
            menor_custo_item = ProjetoDestaque(codigo=cub.codigo_padrao, nome=nome, valor_m2=val)

        if cub.variacao_mensal_pct is not None:
            if maior_alta_item is None or cub.variacao_mensal_pct > maior_alta_item.variacao_pct:
                maior_alta_item = ProjetoDestaque(codigo=cub.codigo_padrao, nome=nome, valor_m2=val, variacao_pct=cub.variacao_mensal_pct)
            if maior_queda_item is None or cub.variacao_mensal_pct < maior_queda_item.variacao_pct:
                maior_queda_item = ProjetoDestaque(codigo=cub.codigo_padrao, nome=nome, valor_m2=val, variacao_pct=cub.variacao_mensal_pct)

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
# 4. IMPACTO DA DESONERAÇÃO CONCISO /deson (com cache Redis)
# ==============================================================================

@router.get(
    "/{uf}/deson",
    response_model=ImpactoDesoneracaoResponse,
    summary="Impacto tributário da desoneração da folha CPRB (economia por m²)",
    description=(
        "**Dor que resolve:** Decisões de planejamento tributário e orçamentos de licitação pública exigem saber "
        "com precisão matemática qual é a vantagem de optar pela desoneração da folha de pagamento (CPRB / Lei 12.546/2011). "
        "Este endpoint cruza as cotações COM e SEM desoneração para cada projeto-padrão da UF.\n\n"
        "**Retorno:** Economia absoluta em reais por metro quadrado (`R$/m²`), percentual de economia (`%`) "
        "e projeto de maior benefício fiscal da praça."
    )
)
@router.get("/{uf}/impacto-desoneracao", response_model=ImpactoDesoneracaoResponse, include_in_schema=False)
@cache_response(ttl=86400, prefix="cub:deson")
def get_impacto_desoneracao(
    uf: str,
    ano: Optional[int] = Query(None, description="Ano de referência (ex: 2026)", examples=[2026]),
    mes: Optional[int] = Query(None, description="Mês de referência (1 a 12)", examples=[8]),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon específico"),
    db: Session = Depends(get_db)
):
    """Cruzamento pré-calculado das séries COM e SEM desoneração."""

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
# 5. RANKING NACIONAL CONCISO /rank (com cache Redis)
# ==============================================================================

@router.get(
    "/rank",
    response_model=RankingResponse,
    summary="Ranking nacional de estados por projeto-padrão (cacheado)",
    description=(
        "**Dor que resolve:** Benchmarking de competitividade e custo territorial. Permite ranquear rapidamente "
        "todos os estados brasileiros do mais caro ao mais barato para um determinado padrão construtivo (ex: R8-N, R1-N, GI), "
        "calculando automaticamente a média nacional e o desvio percentual (`desvio_media_pct`) de cada praça."
    )
)
@router.get("/ranking", response_model=RankingResponse, include_in_schema=False)
@cache_response(ttl=86400, prefix="cub:rank")
def get_cub_rank(
    codigo_padrao: str = Query("R1-N", description="Código do padrão normativo (ex: R1-N, R8-N, GI)", examples=["R8-N"]),
    ano: Optional[int] = Query(None, description="Ano de referência (ex: 2026)", examples=[2026]),
    mes: Optional[int] = Query(None, description="Mês de referência (1 a 12)", examples=[8]),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'", examples=["SEM_DESONERACAO"]),
    db: Session = Depends(get_db)
):
    """Classifica estados pelo valor do m² e calcula desvio da média nacional."""

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
        raise HTTPException(status_code=404, detail=f"Sem dados para {codigo_padrao_norm} em {target_date}.")

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
# 6. SÉRIE HISTÓRICA CONCISA /hist/{cod} (com cache Redis)
# ==============================================================================

@router.get(
    "/{uf}/hist/{codigo_padrao}",
    response_model=CubHistoricoResponse,
    summary="Série histórica e inflação setorial acumulada (cacheado)",
    description=(
        "**Dor que resolve:** Reajustes contratuais de obras, previsões financeiras e teses jurídicas "
        "exigem calcular a variação acumulada do CUB ao longo de meses ou anos. Este endpoint entrega "
        "a série cronológica completa e calcula automaticamente a **inflação acumulada total** no período (`variacao_acumulada_pct`).\n\n"
        "**Rota curta byte-saving:** Substitui a rota mais longa `/historico`."
    )
)
@router.get("/{uf}/historico/{codigo_padrao}", response_model=CubHistoricoResponse, include_in_schema=False)
@cache_response(ttl=86400, prefix="cub:hist")
def get_historico_padrao(
    uf: str,
    codigo_padrao: str,
    ano_inicio: Optional[int] = Query(None, description="Ano inicial do período (ex: 2024)", examples=[2024]),
    ano_fim: Optional[int] = Query(None, description="Ano final do período (ex: 2026)", examples=[2026]),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'", examples=["SEM_DESONERACAO"]),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon específico"),
    db: Session = Depends(get_db)
):
    """Série temporal com variação acumulada no período e métricas consolidadas."""

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
        raise HTTPException(status_code=404, detail=f"Sem histórico para {uf_upper}/{codigo_padrao_norm}.")

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
# 7. COMPARATIVO CONCISO /comp E CONSULTA POR UF
# ==============================================================================

@router.get(
    "/comp",
    response_model=ComparativoResponse,
    summary="Comparativo regional de custos entre múltiplos estados",
    description=(
        "**Dor que resolve:** Incorporadoras em expansão geográfica ou orçamentistas corporativos "
        "precisam avaliar custos relativos entre praças diferentes para tomada de decisão de investimento. "
        "Este endpoint compara o custo do m² para o mesmo projeto-padrão entre múltiplos estados informados "
        "(ex: `ufs=GO,MG,PR,SP`) em uma única consulta, calculando a média do grupo e o desvio relativo de cada estado."
    )
)
@router.get("/comparativo", response_model=ComparativoResponse, include_in_schema=False)
def get_comparativo_regional(
    ufs: str = Query(..., description="Lista de UFs separadas por vírgula (ex: GO,MG,PR,RJ)", examples=["GO,MG,PR,SP"]),
    codigo_padrao: str = Query("R1-N", description="Código do projeto-padrão (ex: R1-N, R8-N, CSL-8-N)", examples=["R8-N"]),
    ano: Optional[int] = Query(None, description="Ano de referência (ex: 2026)", examples=[2026]),
    mes: Optional[int] = Query(None, description="Mês de referência (1 a 12)", examples=[8]),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'", examples=["SEM_DESONERACAO"]),
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

    results = query.order_by(CubMensal.valor_m2.desc()).all()
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum dado encontrado para o padrão {codigo_padrao_norm} nas UFs: {lista_ufs}."
        )

    valores = [c.valor_m2 for c, s in results]
    media_grp = round(sum(valores) / len(valores), 2) if valores else Decimal("0.00")

    items = []
    for cub, sind in results:
        diff = cub.valor_m2 - media_grp
        diff_pct = round((diff / media_grp) * 100, 2) if media_grp > 0 else Decimal("0.00")
        items.append(
            ComparativoItem(
                uf=sind.uf,
                sinduscon_nome=sind.nome,
                regiao=sind.regiao,
                valor_m2=cub.valor_m2,
                diferenca_media_reais=diff,
                diferenca_media_pct=diff_pct,
                variacao_mensal_pct=cub.variacao_mensal_pct
            )
        )

    return ComparativoResponse(
        codigo_padrao=codigo_padrao_norm,
        padrao_nome=padrao_nome,
        data_referencia=data_ref,
        desoneracao=deson_slug,
        total_comparados=len(items),
        media_grupo=media_grp,
        comparativo=items
    )


@router.get(
    "/{uf}",
    response_model=List[CubEstadoPeriodoResponse],
    summary="Consulta cotações do CUB por estado (com filtros de período e regime)",
    description=(
        "**Dor que resolve:** Ponto de entrada padrão para consultas diretas aos 19 projetos da NBR 12.721:2006 "
        "de uma determinada unidade federativa. Permite filtrar por ano, mês, regime de desoneração e sindicato "
        "(para UFs com múltiplos sindicatos cadastrados, como MG e PR).\n\n"
        "**Retorno:** Lista de cotações contendo valores de m², variações mensais e especificações de acabamento."
    )
)
def get_cub_by_uf(
    uf: str,
    ano: Optional[int] = Query(None, description="Ano de referência (ex: 2026)", examples=[2026]),
    mes: Optional[int] = Query(None, description="Mês de referência (1 a 12)", examples=[8]),
    desoneracao: str = Query("SEM_DESONERACAO", description="'SEM_DESONERACAO' ou 'COM_DESONERACAO'", examples=["SEM_DESONERACAO"]),
    sinduscon_id: Optional[int] = Query(None, description="ID do Sinduscon específico"),
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
