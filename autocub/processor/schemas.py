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
    ambiente: str = Field(
        ...,
        description="Nome ou tipo do ambiente (ex: 'Apartamento Privativo', 'Garagem Coberta', 'Varanda Gourmet', 'Pilotis').",
        examples=["Apartamento Privativo"]
    )
    area_real_m2: Decimal = Field(
        ...,
        gt=0,
        description="Área real física construída do ambiente em metros quadrados (m²).",
        examples=[Decimal("120.00")]
    )
    fator_ponderacao: Optional[Decimal] = Field(
        None,
        ge=0,
        le=2.0,
        description="Fator de equivalência customizado. Se omitido (null), a API resolve e aplica automaticamente o fator normativo canônico da NBR 12.721:2006 (Quadro II).",
        examples=[Decimal("1.00")]
    )


class CalculoAreaRequest(BaseModel):
    itens: List[AreaItemInput] = Field(
        ...,
        min_length=1,
        description="Lista de ambientes da edificação com suas áreas reais para cálculo da área equivalente ponderada.",
        examples=[
            [
                {"ambiente": "Apartamento Privativo", "area_real_m2": 100.0, "fator_ponderacao": 1.0},
                {"ambiente": "Garagem Coberta (Subsolo)", "area_real_m2": 25.0, "fator_ponderacao": 0.65},
                {"ambiente": "Varanda Gourmet", "area_real_m2": 10.0, "fator_ponderacao": 0.50}
            ]
        ]
    )
    cub_m2: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Valor do CUB/m² (R$) para estimativa de custo global. Se informado, calcula o valor orçado (Área Equivalente × CUB).",
        examples=[Decimal("2623.20")]
    )
    uf: Optional[str] = Field(
        None,
        description="Sigla da UF (ex: GO, MG, RJ). Se informado junto com 'codigo_padrao', busca o CUB mais recente do banco.",
        examples=["GO"]
    )
    codigo_padrao: Optional[str] = Field(
        None,
        description="Código do projeto-padrão (ex: R1-N, R8-N, PP-4-N) para consulta automática do CUB.",
        examples=["R8-N"]
    )


class AreaItemOutput(BaseModel):
    ambiente: str = Field(..., description="Nome ou tipo do ambiente informado.")
    area_real_m2: Decimal = Field(..., description="Área real física em m².")
    fator_utilizado: Decimal = Field(..., description="Fator de ponderação aplicado segundo a NBR 12.721:2006.")
    area_equivalente_m2: Decimal = Field(..., description="Área equivalente resultante (Área Real × Fator).")


class AreaEquivalenteResponse(BaseModel):
    area_real_total_m2: Decimal = Field(..., description="Soma das áreas reais físicas de todos os ambientes.")
    area_equivalente_total_m2: Decimal = Field(..., description="Área equivalente ponderada total da edificação segundo a NBR 12.721.")
    fator_equivalente_medio: Decimal = Field(..., description="Fator médio de ponderação global da obra (Área Equivalente / Área Real).")
    cub_m2_aplicado: Optional[Decimal] = Field(None, description="Valor do CUB/m² utilizado no cálculo (se informado ou consultado).")
    custo_estimado_total: Optional[Decimal] = Field(None, description="Estimativa de Custo Global (R$) = Área Equivalente Total × CUB/m².")
    itens: List[AreaItemOutput] = Field(..., description="Detalhamento individual de cada ambiente.")
    nota_normativa: str = Field(
        "Conforme a ABNT NBR 12.721:2006 (Quadro II), a multiplicação do CUB/m² deve ser efetuada sempre sobre a Área Equivalente Total, e jamais sobre a Área Real física. O CUB não contempla fundações especiais, elevadores, urbanização e BDI.",
        description="Fundamentação técnica e legal do método de cálculo."
    )


class FatorAreaItem(BaseModel):
    tipo_ambiente: str = Field(..., description="Classificação do ambiente.")
    fator_padrao: Decimal = Field(..., description="Coeficiente padrão de ponderação (NBR 12.721 Quadro II).")
    faixa_recomendada: str = Field(..., description="Intervalo normativo recomendado.")
    descricao: str = Field(..., description="Orientações de aplicação segundo a norma.")


class FatoresNormativosResponse(BaseModel):
    norma: str = "ABNT NBR 12.721:2006 — Quadro II"
    descricao: str = "Coeficientes canônicos para cálculo da Área Equivalente de Construção."
    fatores: List[FatorAreaItem]


