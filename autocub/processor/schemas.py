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


# ==============================================================================
# Schemas de Resposta da API RESTful (Mimetizando autoSINAPI e Mundo AEC)
# ==============================================================================

class PadraoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    codigo_base: str
    nome: str
    categoria: str
    padrao_acabamento: str
    pavimentos: Optional[int] = None
    area_real: Optional[Decimal] = None
    area_equivalente: Optional[Decimal] = None
    dormitorios: Optional[int] = None
    vagas_garagem: Optional[int] = None
    elevadores: Optional[int] = None
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

    uf: Optional[str] = None
    sinduscon_id: Optional[int] = None
    sinduscon_nome: Optional[str] = None
    regiao: Optional[str] = None
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
    regiao: Optional[str] = None
    data_referencia: date
    desoneracao: str
    total_projetos: int
    cotacoes: List[CubCotacaoResponse]


class CubHistoricoItem(BaseModel):
    data_referencia: date
    valor_m2: Decimal
    variacao_mensal_pct: Optional[Decimal] = None
    variacao_acumulada_pct: Optional[Decimal] = None


class CubHistoricoResponse(BaseModel):
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    codigo_padrao: str
    padrao_nome: str
    desoneracao: str
    total_meses: int
    valor_inicial: Optional[Decimal] = None
    valor_final: Optional[Decimal] = None
    variacao_acumulada_periodo_pct: Optional[Decimal] = None
    variacao_media_mensal_pct: Optional[Decimal] = None
    menor_valor_m2: Optional[Decimal] = None
    maior_valor_m2: Optional[Decimal] = None
    serie_historica: List[CubHistoricoItem]


class ComparativoItem(BaseModel):
    uf: str
    sinduscon_nome: str
    regiao: Optional[str] = None
    valor_m2: Decimal
    variacao_mensal_pct: Optional[Decimal] = None


class ComparativoResponse(BaseModel):
    codigo_padrao: str
    padrao_nome: str
    data_referencia: date
    desoneracao: str
    total_comparados: int
    media_grupo: Decimal
    comparativo: List[ComparativoItem]


# ------------------------------------------------------------------------------
# Schemas para Inteligência Analítica Pré-calculada (Padrão autoSINAPI / BI)
# ------------------------------------------------------------------------------

class ProjetoDestaque(BaseModel):
    codigo: str
    nome: str
    valor_m2: Optional[Decimal] = None
    variacao_pct: Optional[Decimal] = None


class PanoramaMetricas(BaseModel):
    media_geral_m2: Decimal
    media_residencial_m2: Decimal
    media_comercial_m2: Decimal
    media_especial_m2: Decimal
    maior_custo: ProjetoDestaque
    menor_custo: ProjetoDestaque
    maior_alta_mensal: Optional[ProjetoDestaque] = None
    maior_queda_mensal: Optional[ProjetoDestaque] = None


class BlocoPadroes(BaseModel):
    total_projetos: int
    media_m2: Decimal
    projetos: List[CubCotacaoResponse]


class PanoramaEstruturaAgrupada(BaseModel):
    residencial: Dict[str, BlocoPadroes]
    comercial: Dict[str, BlocoPadroes]
    especial: Dict[str, BlocoPadroes]


class PanoramaResponse(BaseModel):
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    regiao: str
    data_referencia: date
    desoneracao: str
    total_projetos: int
    metricas: PanoramaMetricas
    estrutura_agrupada: PanoramaEstruturaAgrupada


class ItemImpactoDesoneracao(BaseModel):
    codigo_padrao: str
    padrao_nome: str
    categoria: str
    padrao_acabamento: str
    valor_sem_desoneracao: Decimal
    valor_com_desoneracao: Decimal
    economia_reais_m2: Decimal
    economia_percentual: Decimal


class ImpactoDesoneracaoResponse(BaseModel):
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    data_referencia: date
    economia_media_reais_m2: Decimal
    economia_media_percentual: Decimal
    projetos: List[ItemImpactoDesoneracao]


class RankingItem(BaseModel):
    posicao: int
    uf: str
    sinduscon_nome: str
    regiao: str
    valor_m2: Decimal
    variacao_mensal_pct: Optional[Decimal] = None
    desvio_media_pct: Decimal


class RankingResponse(BaseModel):
    codigo_padrao: str
    padrao_nome: str
    data_referencia: date
    desoneracao: str
    total_estados: int
    media_nacional: Decimal
    ranking: List[RankingItem]


class EtlTriggerResponse(BaseModel):
    task_id: str
    status: str
    mensagem: str


class CubBrasilItem(BaseModel):
    uf: str
    sinduscon_nome: str
    regiao: str
    projeto_representativo: str
    peso_relativo: Decimal
    valor_m2: Decimal
    participacao_efetiva_pct: Decimal


class CubBrasilResponse(BaseModel):
    data_referencia: date
    desoneracao: str
    cub_medio_brasil: Decimal
    total_estados_ponderados: int
    soma_pesos: Decimal
    por_regiao: Dict[str, Decimal]
    estados: List[CubBrasilItem]


class AreaItemInput(BaseModel):
    ambiente: str  # ex: "Apartamento Tipo", "Garagem Coberta", "Varanda"
    area_real_m2: Decimal
    fator_ponderacao: Optional[Decimal] = None  # Se omitido, usa sugestão NBR


class AreaItemOutput(BaseModel):
    ambiente: str
    area_real_m2: Decimal
    fator_utilizado: Decimal
    area_equivalente_m2: Decimal


class AreaEquivalenteResponse(BaseModel):
    area_real_total_m2: Decimal
    area_equivalente_total_m2: Decimal
    fator_equivalente_medio: Decimal
    itens: List[AreaItemOutput]

