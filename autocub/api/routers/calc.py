from decimal import Decimal
from typing import List, Union, Optional
from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from autocub.database.connection import get_db
from autocub.database.models import CubMensal, Sinduscon
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
        "**Exemplo de entrada aceito:** Objeto `CalculoAreaRequest` completo ou lista direta `[AreaItemInput]`."
    )
)
def calcular_area_equivalente(
    payload: Union[CalculoAreaRequest, List[AreaItemInput]] = Body(
        ...,
        description="Parâmetros de cálculo. Pode ser o objeto completo CalculoAreaRequest ou uma lista direta de itens.",
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
    if isinstance(payload, list):
        itens = payload
        cub_m2 = None
        uf = None
        codigo_padrao = None
    else:
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

    # Resolução automática de CUB se UF e padrão forem fornecidos sem CUB explícito
    cub_aplicado = cub_m2
    if cub_aplicado is None and uf and codigo_padrao:
        sind = db.query(Sinduscon).filter(Sinduscon.uf == uf.upper(), Sinduscon.ativo == True).first()
        if sind:
            cotacao = (
                db.query(CubMensal)
                .filter(
                    CubMensal.sinduscon_id == sind.id,
                    CubMensal.codigo_padrao == codigo_padrao.upper()
                )
                .order_by(desc(CubMensal.data_referencia))
                .first()
            )
            if cotacao:
                cub_aplicado = cotacao.valor_m2

    custo_total = round(total_equiv * cub_aplicado, 2) if cub_aplicado is not None else None

    return AreaEquivalenteResponse(
        area_real_total_m2=total_real,
        area_equivalente_total_m2=total_equiv,
        fator_equivalente_medio=fator_medio,
        cub_m2_aplicado=cub_aplicado,
        custo_estimado_total=custo_total,
        itens=outputs
    )
