from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict
from autocub.core.numerico import Num  # ADR 009


class CubItemExtracted(BaseModel):
    categoria: str
    padrao: str
    codigo_base: str
    codigo_canonico: str
    valor_m2: Decimal
    variacao_pct: Optional[Num] = None


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
    area_real: Optional[Num] = None
    area_equivalente: Optional[Num] = None
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
    valor_m2: Num
    variacao_mensal_pct: Optional[Num] = None
    desoneracao: str
    data_referencia: date


class CubLatestResposta(BaseModel):
    """Envelope de `/latest` quando a UF consultada não tem adapter/dado
    publicado (LIM-38 — decisão 2026-09-30: nota no response, em vez de
    `[]` vazio). O caminho normal continua sendo a lista plana."""
    uf: Optional[str] = None
    items: List[CubCotacaoResponse] = Field(default_factory=list)
    nota_lim38: str


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
    valor_m2: Num
    variacao_mensal_pct: Optional[Num] = None
    variacao_acumulada_pct: Optional[Num] = None


class CubHistoricoResponse(BaseModel):
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    codigo_padrao: str
    padrao_nome: str
    desoneracao: str
    total_meses: int
    valor_inicial: Optional[Num] = None
    valor_final: Optional[Num] = None
    variacao_acumulada_periodo_pct: Optional[Num] = None
    variacao_media_mensal_pct: Optional[Num] = None
    menor_valor_m2: Optional[Num] = None
    maior_valor_m2: Optional[Num] = None
    serie_historica: List[CubHistoricoItem]


class ComparativoItem(BaseModel):
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    regiao: Optional[str] = None
    valor_m2: Num
    variacao_mensal_pct: Optional[Num] = None
    data_referencia: Optional[date] = None
    """STORY-MCP-007/B-02: a competência **deste** item. A consulta usa uma
    data única, então hoje coincide com o envelope — mas expor por item é o que
    permite ao agente auditar cada linha sem inferir, e detectar divergência se
    a consulta passar a admitir referências distintas por UF."""


class ComparativoResponse(BaseModel):
    codigo_padrao: str
    padrao_nome: str
    data_referencia: date
    desoneracao: str
    total_comparados: int
    media_grupo: Num
    comparativo: List[ComparativoItem]
    ufs_nao_encontrados: List[str] = []
    """§5.4: UFs pedidas no `ufs` sem sinduscon/dado para o padrão+mês —
    nunca descartadas em silêncio (ex.: SP sem adapter de coleta)."""


# ------------------------------------------------------------------------------
# Schemas para Inteligência Analítica Pré-calculada (Padrão autoSINAPI / BI)
# ------------------------------------------------------------------------------

class ProjetoDestaque(BaseModel):
    codigo: str
    nome: str
    valor_m2: Optional[Num] = None
    variacao_pct: Optional[Num] = None


class PanoramaMetricas(BaseModel):
    media_geral_m2: Num
    media_residencial_m2: Num
    media_comercial_m2: Num
    media_especial_m2: Num
    maior_custo: ProjetoDestaque
    menor_custo: ProjetoDestaque
    maior_alta_mensal: Optional[ProjetoDestaque] = None
    maior_queda_mensal: Optional[ProjetoDestaque] = None


class BlocoPadroes(BaseModel):
    total_projetos: int
    media_m2: Num
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
    fonte: str
    """§5.8: origem do dado em texto único para sinalização ao usuário —
    sindicato publicador, norma e período de referência (ex.: "Sinduscon-MG
    (MG) — CUB publicado (NBR 12.721:2006), referência 2026-01")."""


class ItemImpactoDesoneracao(BaseModel):
    codigo_padrao: str
    padrao_nome: str
    categoria: str
    padrao_acabamento: str
    valor_sem_desoneracao: Num
    valor_com_desoneracao: Num
    economia_reais_m2: Num
    economia_percentual: Num


class ImpactoDesoneracaoResponse(BaseModel):
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    data_referencia: date
    economia_media_reais_m2: Num
    economia_media_percentual: Num
    projetos: List[ItemImpactoDesoneracao]


class RankingItem(BaseModel):
    posicao: int
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    regiao: str
    valor_m2: Num
    variacao_mensal_pct: Optional[Num] = None
    desvio_media_pct: Num


class RankingResponse(BaseModel):
    codigo_padrao: str
    padrao_nome: str
    data_referencia: date
    desoneracao: str
    total_estados: int
    media_nacional: Num
    ufs_incluidas: List[str] = []
    """§5.3: UFs que efetivamente entraram na média (a "média nacional" é
    uma AMOSTRA — declarar quem compõe, nunca esconder a cobertura)."""
    cobertura_pct: Decimal = Decimal("0.0")
    """§5.3: cobertura da amostra (% das 27 UFs do Brasil)."""
    ranking: List[RankingItem]


class EtlTriggerResponse(BaseModel):
    task_id: str
    status: str
    mensagem: str


class CubBrasilItem(BaseModel):
    uf: str
    sinduscon_id: int
    sinduscon_nome: str
    regiao: str
    projeto_representativo: str
    peso_relativo: Num
    valor_m2: Num
    participacao_efetiva_pct: Num


class CubBrasilResponse(BaseModel):
    data_referencia: date
    desoneracao: str
    cub_medio_brasil: Num
    total_estados_ponderados: int
    soma_pesos: Num
    por_regiao: Dict[str, Num]
    estados: List[CubBrasilItem]


class AreaItemInput(BaseModel):
    ambiente: str = Field(
        ...,
        description="Nome ou tipo do ambiente (ex: 'Apartamento Privativo', 'Garagem Coberta', 'Varanda Gourmet', 'Pilotis').",
        examples=["Apartamento Privativo"]
    )
    area_real_m2: Num = Field(
        ...,
        gt=0,
        description="Área real física construída do ambiente em metros quadrados (m²).",
        examples=[Decimal("120.00")]
    )
    fator_ponderacao: Optional[Num] = Field(
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
    cub_m2: Optional[Num] = Field(
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
    area_real_m2: Num = Field(..., description="Área real física em m².")
    fator_utilizado: Num = Field(..., description="Fator de ponderação aplicado segundo a NBR 12.721:2006.")
    area_equivalente_m2: Num = Field(..., description="Área equivalente resultante (Área Real × Fator).")


class AreaEquivalenteResponse(BaseModel):
    area_real_total_m2: Num = Field(..., description="Soma das áreas reais físicas de todos os ambientes.")
    area_equivalente_total_m2: Num = Field(..., description="Área equivalente ponderada total da edificação segundo a NBR 12.721.")
    fator_equivalente_medio: Num = Field(..., description="Fator médio de ponderação global da obra (Área Equivalente / Área Real).")
    cub_m2_aplicado: Optional[Num] = Field(None, description="Valor do CUB/m² utilizado no cálculo (se informado ou consultado).")
    custo_estimado_total: Optional[Num] = Field(None, description="Estimativa de Custo Global (R$) = Área Equivalente Total × CUB/m².")
    erro: Optional[str] = Field(
        None,
        description="STORY-MCP-007/C-04: código do que impediu o orçamento "
        "(ex.: `CUB_INDISPONIVEL_PARA_UF`). Nunca haverá `custo_estimado_total: null` "
        "sem este campo — orçamento em branco sem aviso é pior que erro.",
        examples=["CUB_INDISPONIVEL_PARA_UF", "CUB_NAO_INFORMADO"],
    )
    motivo: Optional[str] = Field(
        None,
        description="Explicação legível do erro (qual UF, o que foi pedido, o que falta).",
    )
    ufs_com_cub_mais_proximas: Optional[List[str]] = Field(
        None,
        description="UFs vizinhas (ou as mais próximas em cobertura) que possuem CUB "
        "publicado — sugestão de fallback para o agente seguir em vez de devolver branco.",
        examples=[["MG", "RJ"]],
    )
    itens: List[AreaItemOutput] = Field(..., description="Detalhamento individual de cada ambiente.")
    nota_normativa: str = Field(
        "Conforme a ABNT NBR 12.721:2006 (Quadro II), a multiplicação do CUB/m² deve ser efetuada sempre sobre a Área Equivalente Total, e jamais sobre a Área Real física. O CUB não contempla fundações especiais, elevadores, urbanização e BDI.",
        description="Fundamentação técnica e legal do método de cálculo."
    )


class FatorAreaItem(BaseModel):
    tipo_ambiente: str = Field(..., description="Classificação do ambiente.")
    fator_padrao: Num = Field(..., description="Coeficiente padrão de ponderação (NBR 12.721 Quadro II).")
    faixa_recomendada: str = Field(..., description="Intervalo normativo recomendado.")
    descricao: str = Field(..., description="Orientações de aplicação segundo a norma.")


class FatoresNormativosResponse(BaseModel):
    norma: str = "ABNT NBR 12.721:2006 — Quadro II"
    descricao: str = "Coeficientes canônicos para cálculo da Área Equivalente de Construção."
    fatores: List[FatorAreaItem]


