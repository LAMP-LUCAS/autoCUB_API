from typing import Dict, Any, List
from fastapi import APIRouter
from autocub.adapters.registry import AdapterRegistry
from autocub.core.cache import cache_response

router = APIRouter(prefix="/kb", tags=["Base de Conhecimento Perene & Normas"])


@router.get(
    "/faq",
    summary="Perguntas frequentes e lista oficial dos 8 itens excluídos do CUB",
    description=(
        "**Dor que resolve:** Erros graves de orçamento e disputas judiciais ocorrem quando o incorporador "
        "ou cliente presume que o CUB contempla o custo total de uma obra. O Item 8.3.5 da NBR 12.721:2006 "
        "determina que o CUB **não inclui** itens como fundações especiais, elevadores, instalações de ar condicionado, "
        "obras de urbanização/lazer, projetos, impostos e BDI/lucro da construtora.\n\n"
        "**Retorno:** FAQ oficial consolidado das cartilhas da CBIC e a discriminação dos 8 itens excluídos."
    )
)
@cache_response(ttl=604800, prefix="kb:faq")
def get_kb_faq() -> Dict[str, Any]:
    """Retorna o FAQ oficial e os itens desconsiderados na formação do CUB."""
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    return {
        "itens_excluidos_do_cub": adapter.get_itens_excluidos_cub(),
        "faq": adapter.get_faq()
    }


@router.get(
    "/insumos",
    summary="Lote básico dos 29 insumos e 4 famílias macro da NBR 12.721",
    description=(
        "**Dor que resolve:** Dá transparência e inteligência analítica à cesta de custos da construção civil. "
        "Permite que engenheiros orçamentistas identifiquem a sensibilidade de cada grupo de custos (Materiais, "
        "Mão de Obra, Equipamento e Despesa Administrativa) no índice global.\n\n"
        "**Retorno:** Relação dos 29 insumos padronizados com seus respectivos pesos médios percentuais na formação do CUB."
    )
)
@cache_response(ttl=604800, prefix="kb:insumos")
def get_kb_insumos() -> Dict[str, Any]:
    """Retorna a cesta básica dos 29 insumos normatizados pela ABNT."""
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    return adapter.get_lote_insumos()


@router.get(
    "/lei",
    summary="Fundamentos da Lei Federal 4.591/1964 e jurisprudência vinculante do STJ",
    description=(
        "**Dor que resolve:** Garante segurança jurídica na elaboração de contratos imobiliários de compra e venda "
        "na planta e memoriais de incorporação (Quadro I a IV).\n\n"
        "**Retorno:** Resumo dos Artigos 53, 54 e 55 da Lei Federal nº 4.591/1964, a regra de divulgação até o "
        "5º dia útil e a pacificação jurisprudencial do Superior Tribunal de Justiça (STJ) que veda o uso do CUB "
        "como índice de reajuste após a conclusão e entrega das chaves da obra."
    )
)
@cache_response(ttl=604800, prefix="kb:lei")
def get_kb_lei() -> Dict[str, Any]:
    """Retorna a fundamentação legal e teses jurídicas pacificadas sobre o CUB."""
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    return adapter.get_fundamentacao_legal()


@router.get(
    "/nbr",
    summary="Fatores normativos de equivalência de custo (Quadro II NBR 12.721)",
    description=(
        "**Dor que resolve:** Consulta rápida aos parâmetros técnicos recomendados pela ABNT para orçamentação "
        "de garagens, varandas, pilotis e terraços descobertos.\n\n"
        "**Retorno:** Fatores canônicos de ponderação para cálculo da área equivalente de custo da edificação."
    )
)
@cache_response(ttl=604800, prefix="kb:nbr")
def get_kb_nbr() -> Dict[str, Any]:
    """Retorna os fatores padrão de equivalência de área da NBR 12.721."""
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    return {
        "fatores_area_equivalente": adapter.get_fatores_area_equivalente(),
        "instrucoes_de_uso": "Multiplique cada área real pelo seu fator de equivalência para obter a área virtual equivalente que deve ser multiplicada pelo CUB/m²."
    }

