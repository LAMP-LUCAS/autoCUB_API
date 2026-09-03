from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from autocub.database.connection import get_db
from autocub.database.models import Sinduscon, PadraoProjeto
from autocub.processor.schemas import SindusconResponse, PadraoResponse

router = APIRouter(prefix="", tags=["Metadados & Padrões Construtivos"])


@router.get(
    "/sinduscons",
    response_model=List[SindusconResponse],
    summary="Lista os Sinduscons cadastrados e mapeados",
    description=(
        "**Dor que resolve:** Identifica oficialmente qual é a entidade patronal e o sindicato legalmente "
        "responsável pelo cálculo e publicação do CUB em cada UF ou região do Brasil.\n\n"
        "**Retorno:** Relação completa de sindicatos ativos, com código ID canônico adotado pelo portal central "
        "da CBIC (`cub.org.br`), nome oficial e macrorregião geográfica."
    )
)
def list_sinduscons(
    uf: Optional[str] = Query(None, description="Filtrar por UF (ex: GO, MG, PR)", examples=["GO"]),
    regiao: Optional[str] = Query(None, description="Filtrar por macrorregião (ex: SUDESTE, CENTRO-OESTE)", examples=["CENTRO-OESTE"]),
    ativo_apenas: bool = Query(True, description="Apenas sindicatos ativos no portal"),
    db: Session = Depends(get_db)
):
    """Retorna os sindicatos da indústria da construção civil cadastrados."""
    query = db.query(Sinduscon)
    if ativo_apenas:
        query = query.filter(Sinduscon.ativo == True)
    if uf:
        query = query.filter(Sinduscon.uf == uf.upper())
    if regiao:
        query = query.filter(Sinduscon.regiao == regiao.upper())

    return query.order_by(Sinduscon.uf, Sinduscon.nome).all()


@router.get(
    "/padroes",
    response_model=List[PadraoResponse],
    summary="Lista os 19 projetos-padrão da NBR 12.721:2006",
    description=(
        "**Dor que resolve:** Resolve a incerteza técnica sobre quais tipologias construtivas existem na norma, "
        "quais são seus parâmetros arquitetônicos oficiais (número de pavimentos, dormitórios, vagas e área real) "
        "e qual o padrão de acabamento correspondente para enquadramento correto de uma obra.\n\n"
        "**Retorno:** Catálogo completo dos 19 projetos normatizados (Residenciais, Comerciais e Especiais)."
    )
)
def list_padroes(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria: RESIDENCIAL, COMERCIAL, ESPECIAL", examples=["RESIDENCIAL"]),
    padrao_acabamento: Optional[str] = Query(None, description="Filtrar por acabamento: BAIXO, NORMAL, ALTO, UNICO", examples=["NORMAL"]),
    db: Session = Depends(get_db)
):
    """Retorna o catálogo normativo dos 19 projetos da ABNT NBR 12.721:2006."""
    query = db.query(PadraoProjeto)
    if categoria:
        query = query.filter(PadraoProjeto.categoria == categoria.upper())
    if padrao_acabamento:
        query = query.filter(PadraoProjeto.padrao_acabamento == padrao_acabamento.upper())

    return query.order_by(PadraoProjeto.categoria, PadraoProjeto.padrao_acabamento, PadraoProjeto.codigo).all()


@router.get(
    "/padroes/{codigo}",
    response_model=PadraoResponse,
    summary="Ficha técnica detalhada de um projeto-padrão específico",
    description=(
        "**Dor que resolve:** Consulta imediata aos atributos e coeficientes físicos de um projeto normatizado "
        "(ex: R8-N, R1-N, PP-4-B, CSL-8, GI), permitindo validar áreas reais, áreas equivalentes e dependências "
        "para memoriais descritivos de incorporação imobiliária (Quadro I da NBR 12.721)."
    )
)
def get_padrao_detail(
    codigo: str,
    db: Session = Depends(get_db)
):
    """Retorna a especificação técnica de um projeto-padrão pelo código normativo."""
    padrao = db.query(PadraoProjeto).filter(PadraoProjeto.codigo == codigo.upper()).first()
    if not padrao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Padrão de projeto '{codigo}' não encontrado na base da NBR 12.721."
        )
    return padrao

