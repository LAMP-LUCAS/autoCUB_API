from decimal import Decimal
from typing import List, Union, Optional
from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from autocub.api.resolvers import resolver_sinduscon
from autocub.database.connection import get_db
from autocub.database.models import CubMensal
from autocub.processor.schemas import (
    AreaItemInput,
    AreaItemOutput,
    AreaEquivalenteResponse,
    CalculoAreaRequest,
    FatorAreaItem,
    FatoresNormativosResponse,
)

router = APIRouter(prefix="/calc", tags=["Calculadoras Paramétricas Normativas"])

# Tabela canônica de fatores padrão (NBR 12.721:2006 Quadro II)
FATORES_CANONICOS = [
    {
        "tipo_ambiente": "Área Privativa Principal (Apartamento / Sala / Casa)",
        "fator_padrao": Decimal("1.00"),
        "faixa_recomendada": "1.00",
        "keywords": ["privativa", "apartamento", "sala", "casa", "tipo", "cobertura privativa"],
        "descricao": "Área de vivência principal coberta com padrão de acabamento integral da unidade."
    },
    {
        "tipo_ambiente": "Garagem Coberta (Subsolo)",
        "fator_padrao": Decimal("0.65"),
        "faixa_recomendada": "0.50 a 0.75",
        "keywords": ["garagem coberta", "subsolo", "vaga coberta", "estacionamento coberto"],
        "descricao": "Estrutura e alvenaria simples, pisos industriais ou cimentados, sem acabamentos nobres."
    },
    {
        "tipo_ambiente": "Garagem Descoberta / Estacionamento",
        "fator_padrao": Decimal("0.12"),
        "faixa_recomendada": "0.10 a 0.20",
        "keywords": ["garagem descoberta", "estacionamento descoberto", "vaga descoberta"],
        "descricao": "Pavimentação asfáltica, blocos intertravados ou brita sobre solo natural."
    },
    {
        "tipo_ambiente": "Varanda / Sacada Coberta",
        "fator_padrao": Decimal("0.50"),
        "faixa_recomendada": "0.50 a 0.75",
        "keywords": ["varanda", "sacada", "alpendre", "gourmet coberta"],
        "descricao": "Área com fechamento parcial de alvenaria e guarda-corpo."
    },
    {
        "tipo_ambiente": "Terraço / Lazer Descoberto",
        "fator_padrao": Decimal("0.30"),
        "faixa_recomendada": "0.30 a 0.60",
        "keywords": ["terraco", "terraço", "lazer descoberto", "deck", "solarium"],
        "descricao": "Impermeabilização e pisos resistentes a intempéries sem cobertura."
    },
    {
        "tipo_ambiente": "Pilotis / Área de Recreação Coberta",
        "fator_padrao": Decimal("0.40"),
        "faixa_recomendada": "0.30 a 0.50",
        "keywords": ["pilotis", "recreacao coberta", "recreação coberta", "hall aberto"],
        "descricao": "Pavimento aberto sob pilotis com pilares e pisos comuns."
    },
    {
        "tipo_ambiente": "Área de Serviço Descoberta / Quintal",
        "fator_padrao": Decimal("0.30"),
        "faixa_recomendada": "0.30 a 0.50",
        "keywords": ["area servico descoberta", "área serviço descoberta", "quintal"],
        "descricao": "Pisos externos com pontos hidráulicos e ralos."
    },
    {
        "tipo_ambiente": "Barrilete / Caixa d'Água / Casa de Máquinas",
        "fator_padrao": Decimal("0.50"),
        "faixa_recomendada": "0.40 a 0.60",
        "keywords": ["barrilete", "caixa d'agua", "caixa d'água", "casa de maquinas", "casa de máquinas"],
        "descricao": "Áreas técnicas de cobertura com impermeabilização e alvenarias de contenção."
    },
]


def resolver_fator_canonico(nome_ambiente: str) -> Decimal:
    """Identifica o fator normativo canônico por correspondência textual com os termos da NBR 12.721."""
    nome_norm = nome_ambiente.lower().strip()
    for item in FATORES_CANONICOS:
        for kw in item["keywords"]:
            if kw in nome_norm:
                return item["fator_padrao"]
    return Decimal("1.00")


@router.get(
    "/fatores",
    response_model=FatoresNormativosResponse,
    summary="Lista fatores canônicos de área equivalente (NBR 12.721)",
    description=(
        "**Dor que resolve:** Evita que incorporadores e orçamentistas apliquem coeficientes empíricos "
        "ou incorretos na homologação de quadros de áreas da NBR 12.721 (Quadro II).\n\n"
        "Retorna os coeficientes padrões e faixas recomendadas pela ABNT para cada tipologia de ambiente."
    )
)
def listar_fatores_normativos():
    """Retorna o catálogo normativo de coeficientes de equivalência de custo."""
    itens = [
        FatorAreaItem(
            tipo_ambiente=f["tipo_ambiente"],
            fator_padrao=f["fator_padrao"],
            faixa_recomendada=f["faixa_recomendada"],
            descricao=f["descricao"]
        )
        for f in FATORES_CANONICOS
    ]
    return FatoresNormativosResponse(fatores=itens)


# Vizinhança por(region/UF) para sugerir fallback quando a UF não tem CUB.
# Prioriza UFs da mesma região (o CUB segue a convenção regional do CBIC) e
# completa com as de maior cobertura — o agente precisa de ALGUMA suggesting
# acionável, não de uma lista vazia.
_UF_POR_REGIAO = {
    "AC": "NORTE", "AM": "NORTE", "AP": "NORTE", "PA": "NORTE", "RO": "NORTE",
    "RR": "NORTE", "TO": "NORTE",
    "AL": "NORDESTE", "BA": "NORDESTE", "CE": "NORDESTE", "MA": "NORDESTE",
    "PB": "NORDESTE", "PE": "NORDESTE", "PI": "NORDESTE", "RN": "NORDESTE",
    "SE": "NORDESTE",
    "DF": "CENTROOESTE", "GO": "CENTROOESTE", "MT": "CENTROOESTE", "MS": "CENTROOESTE",
    "ES": "SUDESTE", "MG": "SUDESTE", "RJ": "SUDESTE", "SP": "SUDESTE",
    "PR": "SUL", "RS": "SUL", "SC": "SUL",
}


def _ufs_com_cub(db: Session, uf: str, limite: int = 5) -> List[str]:
    """UFs com CUB publicado, priorizando a mesma região da UF pedida."""
    from autocub.database.models import Sinduscon

    with_dado = [
        s.uf for s in db.query(Sinduscon.uf).join(
            CubMensal, CubMensal.sinduscon_id == Sinduscon.id
        ).distinct().all()
    ]
    uf = (uf or "").upper()
    regiao = _UF_POR_REGIAO.get(uf)
    mesma_regiao = [u for u in with_dado if _UF_POR_REGIAO.get(u) == regiao and u != uf]
    outras = sorted(u for u in with_dado if u not in mesma_regiao and u != uf)
    return sorted(set(mesma_regiao)) + outras[: limite]


@router.post(
    "/area",
    response_model=AreaEquivalenteResponse,
    summary="Calculadora de Área Equivalente e Orçamento Estimativo (NBR 12.721)",
    description=(
        "**Dor que resolve:** Multiplicar o CUB/m² diretamente sobre a Área Real física de uma edificação "
        "gera uma distorção grave (superavaliação de garagens e terraços ou subavaliação da obra). "
        "A legislação exige converter a construção em **Área Equivalente de Construção** (Quadro II da NBR 12.721).\n\n"
        "**Como funciona:**\n"
        "1. Você envia a lista de ambientes com suas áreas reais em m².\n"
        "2. A API aplica os fatores de equivalência canônicos (ou os customizados informados).\n"
        "3. Se você informar `cub_m2` ou a combinação `uf` + `codigo_padrao`, a API calcula automaticamente o "
        "**Custo Global Estimado da Obra** (`Área Equivalente × CUB/m²`).\n\n"
        "**STORY-MCP-007/C-04:** `payload` é **sempre objeto**. Sem CUB resolvível a resposta "
        "traz `erro` + `motivo` + `ufs_com_cub_mais_proximas` — nunca `custo_estimado_total: null` mudo."
    )
)
def calcular_area_equivalente(
    payload: CalculoAreaRequest = Body(
        ...,
        description="Parâmetros de cálculo (objeto `CalculoAreaRequest`). A forma-lista "
        "foi removida no STORY-MCP-007/C-04: ela perdia a UF e devolvia custo null sem aviso.",
        examples=[
            {
                "cub_m2": 2623.20,
                "uf": "GO",
                "codigo_padrao": "R8-N",
                "itens": [
                    {"ambiente": "Apartamento Privativo", "area_real_m2": 120.0, "fator_ponderacao": 1.0},
                    {"ambiente": "Garagem Coberta (Subsolo)", "area_real_m2": 25.0, "fator_ponderacao": 0.65},
                    {"ambiente": "Varanda Gourmet", "area_real_m2": 15.0, "fator_ponderacao": 0.50},
                    {"ambiente": "Estacionamento Descoberto", "area_real_m2": 12.5, "fator_ponderacao": 0.12}
                ]
            }
        ]
    ),
    db: Session = Depends(get_db)
):
    """
    Calcula a Área Equivalente de Construção (Quadro II da ABNT NBR 12.721)
    e opcionalmente o Custo Global Estimado da Obra.
    """
    itens = payload.itens
    cub_m2 = payload.cub_m2
    uf = payload.uf
    codigo_padrao = payload.codigo_padrao

    if not itens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A lista de itens de área não pode estar vazia."
        )

    outputs: List[AreaItemOutput] = []
    total_real = Decimal("0.00")
    total_equiv = Decimal("0.00")

    for item in itens:
        fator = (
            item.fator_ponderacao
            if item.fator_ponderacao is not None
            else resolver_fator_canonico(item.ambiente)
        )
        area_eq = round(item.area_real_m2 * fator, 2)

        total_real += item.area_real_m2
        total_equiv += area_eq

        outputs.append(
            AreaItemOutput(
                ambiente=item.ambiente,
                area_real_m2=item.area_real_m2,
                fator_utilizado=fator,
                area_equivalente_m2=area_eq
            )
        )

    fator_medio = round(total_equiv / total_real, 4) if total_real > 0 else Decimal("1.0000")

    # Resolução automática do CUB (STORY-MCP-007/C-04): antes exigia `uf` E
    # `codigo_padrao`; o agente que só sabia a UF recebia `null` sem explicação.
    # Agora `uf` sozinha resolve pela cotação mais recente da UF.
    cub_aplicado = cub_m2
    motivo_erro = None
    erro = None
    alternativas = None
    if cub_aplicado is None and uf:
        sind = resolver_sinduscon(db, uf)
        filtros = [CubMensal.sinduscon_id == sind.id] if sind else []
        if sind:
            if codigo_padrao:
                filtros.append(CubMensal.codigo_padrao == codigo_padrao.upper())
            cotacao = (
                db.query(CubMensal)
                .filter(*filtros)
                .order_by(desc(CubMensal.data_referencia))
                .first()
            )
            if cotacao:
                cub_aplicado = cotacao.valor_m2
            else:
                erro = "CUB_INDISPONIVEL_PARA_UF"
                linhas_padrao = (
                    db.query(CubMensal.codigo_padrao)
                    .filter(CubMensal.sinduscon_id == sind.id)
                    .distinct()
                    .limit(10)
                    .all()
                )
                padroes = sorted({linha[0] for linha in linhas_padrao if linha[0]})
                motivo_erro = (
                    f"A UF {uf.upper()} tem sindicato cadastrado, mas não há cotação"
                    + (f" para o padrão {codigo_padrao.upper()}" if codigo_padrao else "")
                    + ". Padrões com dado na UF: "
                    + (", ".join(patroes) if padroes else "nenhum") + "."
                )
        else:
            erro = "CUB_INDISPONIVEL_PARA_UF"
            # Sem jargão interno no corpo (P1-1): o cliente lê esta mensagem.
            motivo_erro = (
                f"O índice CUB ainda não está disponível para a UF {uf.upper()}: "
                "não há série publicada para este estado na fonte oficial."
            )
        if erro:
            alternativas = _ufs_com_cub(db, uf)

    if cub_aplicado is None and erro is None:
        erro = "CUB_NAO_INFORMADO"
        motivo_erro = (
            "Informe `cub_m2` ou `uf` para estimar o custo — sem um dos dois a "
            "Área Equivalente é calculada, mas o orçamento não."
        )

    custo_total = round(total_equiv * cub_aplicado, 2) if cub_aplicado is not None else None

    return AreaEquivalenteResponse(
        area_real_total_m2=total_real,
        area_equivalente_total_m2=total_equiv,
        fator_equivalente_medio=fator_medio,
        cub_m2_aplicado=cub_aplicado,
        custo_estimado_total=custo_total,
        erro=erro,
        motivo=motivo_erro,
        ufs_com_cub_mais_proximas=alternativas,
        itens=outputs
    )
