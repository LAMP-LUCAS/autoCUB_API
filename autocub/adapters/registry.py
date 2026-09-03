from typing import Dict, Type, Optional, List
from autocub.adapters.base import BaseEtlAdapter
from autocub.adapters.monthly_pdf_adapter import CbicMonthlyPdfV1Adapter
from autocub.adapters.crawler_adapter import CbicCrawlerAdapter
from autocub.adapters.booklet_adapter import CbicBookletAdapter


class AdapterRegistry:
    """
    Registro dinâmico e fábrica de adaptadores ETL.
    Permite resolver o adaptador correto por tipo de fonte ou identificador.
    """
    _adapters: Dict[str, BaseEtlAdapter] = {}

    @classmethod
    def register(cls, adapter: BaseEtlAdapter) -> None:
        cls._adapters[adapter.adapter_id] = adapter

    @classmethod
    def get_adapter(cls, adapter_id: str) -> Optional[BaseEtlAdapter]:
        return cls._adapters.get(adapter_id)

    @classmethod
    def find_adapter_for_source(cls, source_type: str, source_reference: str) -> Optional[BaseEtlAdapter]:
        for adapter in cls._adapters.values():
            if adapter.can_handle(source_type, source_reference):
                return adapter
        return None

    @classmethod
    def list_adapters(cls) -> List[str]:
        return list(cls._adapters.keys())


# Registro automático dos adaptadores canônicos
AdapterRegistry.register(CbicMonthlyPdfV1Adapter())
AdapterRegistry.register(CbicCrawlerAdapter())
AdapterRegistry.register(CbicBookletAdapter())
