from pathlib import Path
from typing import Any, Union
from autocub.adapters.base import BaseEtlAdapter, StandardEtlResult
from autocub.processor.parser import parse_cub_pdf
from autocub.core.logging import logger


class CbicMonthlyPdfV1Adapter(BaseEtlAdapter):
    """
    Adaptador específico para extração dos relatórios mensais em formato PDF da CBIC (v1 / 2007-atual).
    Isola a manipulação de pdfplumber e mapeamento dos 19 projetos-padrão da NBR 12.721:2006.
    """
    adapter_id = "cbic_monthly_pdf_v1"
    version = "1.0.0"

    def can_handle(self, source_type: str, source_reference: Any) -> bool:
        if source_type.lower() == "monthly_pdf":
            return True
        if isinstance(source_reference, (str, Path)):
            p = str(source_reference).lower()
            return p.endswith(".pdf") and "cub_" in p
        return False

    def extract(self, source_reference: Union[str, Path, bytes], **kwargs) -> Any:
        if isinstance(source_reference, (str, Path)):
            path = Path(source_reference)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo PDF não encontrado: {path}")
            return path
        return source_reference

    def transform(self, raw_content: Any, **kwargs) -> StandardEtlResult:
        relatorio = parse_cub_pdf(raw_content, **kwargs)
        items_count = len(relatorio.itens)


        return StandardEtlResult(
            adapter_id=self.adapter_id,
            source_identifier=str(raw_content) if isinstance(raw_content, (str, Path)) else "in_memory_pdf",
            status="SUCCESS" if items_count > 0 else "EMPTY",
            records_count=items_count,
            data=relatorio,
            metadata={
                "ano": relatorio.ano,
                "mes": relatorio.mes,
                "data_referencia": str(relatorio.data_referencia),
                "desoneracao": relatorio.desoneracao,
                "sinduscon_nome": relatorio.sinduscon_nome,
                "uf": relatorio.uf
            }
        )
