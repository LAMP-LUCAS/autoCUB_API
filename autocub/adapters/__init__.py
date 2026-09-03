from autocub.adapters.base import BaseEtlAdapter, StandardEtlResult
from autocub.adapters.monthly_pdf_adapter import CbicMonthlyPdfV1Adapter
from autocub.adapters.crawler_adapter import CbicCrawlerAdapter
from autocub.adapters.booklet_adapter import CbicBookletAdapter
from autocub.adapters.registry import AdapterRegistry

__all__ = [
    "BaseEtlAdapter",
    "StandardEtlResult",
    "CbicMonthlyPdfV1Adapter",
    "CbicCrawlerAdapter",
    "CbicBookletAdapter",
    "AdapterRegistry"
]
