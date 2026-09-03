from pathlib import Path
from typing import Optional, Tuple
from autocub.core.config import settings
from autocub.adapters.crawler_adapter import CbicCrawlerAdapter


class CubCollector:
    """
    Fachada para o CbicCrawlerAdapter. Mantém compatibilidade com o ecossistema existente.
    """

    def __init__(
        self,
        download_dir: Optional[str] = None,
        request_delay: Optional[float] = None
    ):
        self.adapter = CbicCrawlerAdapter(
            download_dir=download_dir or settings.CUB_DOWNLOAD_DIR,
            request_delay=request_delay or settings.CUB_REQUEST_DELAY_SECONDS
        )

    def get_cached_pdf_path(
        self,
        uf: str,
        sinduscon_id: int,
        ano: int,
        mes: int,
        desoneracao: str
    ) -> Path:
        return self.adapter.get_cached_pdf_path(uf, sinduscon_id, ano, mes, desoneracao)

    def collect_pdf(
        self,
        uf: str,
        sinduscon_id: int,
        ano: int,
        mes: int,
        desoneracao: str = "sem-desoneracao",
        force_download: bool = False
    ) -> Tuple[Path, bool]:
        return self.adapter.extract(
            None,
            uf=uf,
            sinduscon_id=sinduscon_id,
            ano=ano,
            mes=mes,
            desoneracao=desoneracao,
            force_download=force_download
        )
