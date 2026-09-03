from typing import Dict, Any, List
from fastapi import APIRouter
from autocub.adapters.registry import AdapterRegistry
from autocub.core.cache import cache_response

router = APIRouter(prefix="/kb", tags=["Base de Conhecimento / Normas e Lei"])


@router.get("/faq", summary="Perguntas frequentes e itens inclusos/exclusos no CUB")
@cache_response(ttl=604800, prefix="kb:faq")
def get_kb_faq() -> Dict[str, Any]:
    """
    Retorna o FAQ oficial da CBIC e a discriminação detalhada dos itens NÃO inclusos no CUB
    (Fundações, Elevadores, Lazer, Projetos, Terreno, Lucro/BDI - NBR 12.721 Item 8.3.5).
    """
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    return {
        "itens_excluidos_do_cub": adapter.get_itens_excluidos_cub(),
        "faq": adapter.get_faq()
    }


@router.get("/insumos", summary="Lote básico dos 29 insumos e 4 famílias macro da NBR 12.721")
@cache_response(ttl=604800, prefix="kb:insumos")
def get_kb_insumos() -> Dict[str, Any]:
    """
    Retorna os 29 insumos do lote básico da NBR 12.721:2006 (25 Materiais, 2 Mão de Obra,
    1 Despesa Administrativa e 1 Equipamento) com seus pesos médios percentuais.
    """
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    return adapter.get_lote_insumos()


@router.get("/lei", summary="Fundamentos da Lei Federal 4.591/1964 e jurisprudência STJ")
@cache_response(ttl=604800, prefix="kb:lei")
def get_kb_lei() -> Dict[str, Any]:
    """
    Retorna a base legal do CUB na Lei Federal 4.591/1964 (Arts. 53, 54 e 55),
    a obrigatoriedade de divulgação até o dia 5 e o entendimento vinculante do STJ.
    """
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    return adapter.get_fundamentacao_legal()


@router.get("/nbr", summary="Fatores normativos de equivalência de custo (Quadro II)")
@cache_response(ttl=604800, prefix="kb:nbr")
def get_kb_nbr() -> Dict[str, Any]:
    """
    Retorna os fatores padrão de área equivalente da NBR 12.721 (garagem, varanda, terraço, pilotis)
    utilizados para conversão de áreas reais em áreas de custo padrão.
    """
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    return {
        "fatores_area_equivalente": adapter.get_fatores_area_equivalente(),
        "instrucoes_de_uso": "Multiplique cada área real pelo seu fator de equivalência para obter a área virtual equivalente que deve ser multiplicada pelo CUB/m²."
    }
