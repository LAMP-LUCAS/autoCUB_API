from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict


class CubItemExtracted(BaseModel):
    categoria: str
    padrao: str
    codigo_base: str
    codigo_canonico: str
    valor_m2: Decimal
    variacao_pct: Optional[Decimal] = None


class CubRelatorioExtracted(BaseModel):
    sinduscon_nome: Optional[str] = None
    uf: Optional[str] = None
    mes_nome: Optional[str] = None
    ano: int
    mes: int
    data_referencia: date
    desoneracao: str
    itens: List[CubItemExtracted] = Field(default_factory=list)


# Schemas de Resposta da API RESTful (Mimetizando autoSINAPI e Mundo AEC)

class PadraoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    codigo_base: str
    nome: str
    categoria: str
    padrao_acabamento: str
    pavimentos: Optional[int] = None
    descricao: Optional[str] = None


class SindusconResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uf: str
    nome: str
    regiao: str
    ativo: bool


class CubCotacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo_padrao: str
    padrao_nome: Optional[str] = None
    categoria: Optional[str] = None
    padrao_acabamento: Optional[str] = None
    valor_m2: Decimal
    variacao_mensal_pct: Optional[Decimal] = None
    desoneracao: str
    data_referencia: date


class CubEstadoPeriodoResponse(BaseModel):
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    data_referencia: date
    desoneracao: str
    total_projetos: int
    cotacoes: List[CubCotacaoResponse]


class CubHistoricoItem(BaseModel):
    data_referencia: date
    valor_m2: Decimal
    variacao_mensal_pct: Optional[Decimal] = None


class CubHistoricoResponse(BaseModel):
    uf: str
    sinduscon_nome: str
    codigo_padrao: str
    padrao_nome: str
    desoneracao: str
    total_meses: int
    serie_historica: List[CubHistoricoItem]


class ComparativoItem(BaseModel):
    uf: str
    sinduscon_nome: str
    valor_m2: Decimal
    variacao_mensal_pct: Optional[Decimal] = None


class ComparativoResponse(BaseModel):
    codigo_padrao: str
    padrao_nome: str
    data_referencia: date
    desoneracao: str
    comparativo: List[ComparativoItem]


class EtlTriggerResponse(BaseModel):
    task_id: str
    status: str
    mensagem: str
