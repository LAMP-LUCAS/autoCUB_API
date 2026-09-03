from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from autocub.database.connection import get_db
from autocub.database.models import Sinduscon, PadraoProjeto
from autocub.processor.schemas import SindusconResponse, PadraoResponse

router = APIRouter(prefix="", tags=["Metadados & Normas"])


@router.get("/sinduscons", response_model=List[SindusconResponse], summary="Lista os Sinduscons cadastrados")
def list_sinduscons(
    uf: Optional[str] = Query(None, description="Filtrar por UF (ex: GO, MG, PR)"),
    regiao: Optional[str] = Query(None, description="Filtrar por macro-região (ex: SUDESTE, CENTRO-OESTE)"),
    ativo_apenas: bool = Query(True, description="Apenas entidades ativas"),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de Sinduscons regionais cadastrados, seus códigos CBIC e respectivas UFs.
    """
    query = db.query(Sinduscon)
    if ativo_apenas:
        query = query.filter(Sinduscon.ativo == True)
    if uf:
        query = query.filter(Sinduscon.uf == uf.upper())
    if regiao:
        query = query.filter(Sinduscon.regiao == regiao.upper())

    return query.order_by(Sinduscon.uf, Sinduscon.nome).all()


@router.get("/padroes", response_model=List[PadraoResponse], summary="Lista os 19 Padrões da NBR 12.721:2006")
def list_padroes(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria: RESIDENCIAL, COMERCIAL, ESPECIAL"),
    padrao_acabamento: Optional[str] = Query(None, description="Filtrar por acabamento: BAIXO, NORMAL, ALTO, UNICO"),
    db: Session = Depends(get_db)
):
    """
    Retorna o catálogo completo dos 19 projetos-padrão normalizados pela ABNT NBR 12.721:2006.
    """
    query = db.query(PadraoProjeto)
    if categoria:
        query = query.filter(PadraoProjeto.categoria == categoria.upper())
    if padrao_acabamento:
        query = query.filter(PadraoProjeto.padrao_acabamento == padrao_acabamento.upper())

    return query.order_by(PadraoProjeto.categoria, PadraoProjeto.padrao_acabamento, PadraoProjeto.codigo).all()


@router.get("/padroes/{codigo}", response_model=PadraoResponse, summary="Detalhes de um Padrão Específico")
def get_padrao_detail(
    codigo: str,
    db: Session = Depends(get_db)
):
    """
    Retorna a especificação técnica detalhada de um código de projeto-padrão (ex: R1-N, PP-4-B, CSL-8-A, GI).
    """
    padrao = db.query(PadraoProjeto).filter(PadraoProjeto.codigo == codigo.upper()).first()
    if not padrao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Padrão de projeto '{codigo}' não encontrado na base NBR 12.721."
        )
    return padrao
