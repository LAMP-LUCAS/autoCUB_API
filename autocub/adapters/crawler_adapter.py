import time
import random
from pathlib import Path
from typing import Any, Optional, Tuple
from autocub.adapters.base import BaseEtlAdapter, StandardEtlResult
from autocub.downloader.client import CubHttpClient
from autocub.core.config import settings
from autocub.core.logging import logger


class CbicCrawlerAdapter(BaseEtlAdapter):
    """
    Adaptador para coleta web e download ético junto ao site oficial da CBIC (cub.org.br).
    Isola a gestão de sessões HTTP, CSRF, cookies e rate-limiting com jitter.
    """
    adapter_id = "cbic_crawler_v1"
    version = "1.0.0"

    def __init__(self, download_dir: Optional[str] = None, request_delay: Optional[float] = None):
        self.download_dir = Path(download_dir or settings.CUB_DOWNLOAD_DIR)
        self.request_delay = request_delay or settings.CUB_REQUEST_DELAY_SECONDS
        self.client = CubHttpClient()

    def can_handle(self, source_type: str, source_reference: Any) -> bool:
        return source_type.lower() in ("cbic_web", "web_crawler")

    def get_cached_pdf_path(self, uf: str, sinduscon_id: int, ano: int, mes: int, desoneracao: str) -> Path:
        subfolder = self.download_dir / uf.upper() / str(sinduscon_id)
        subfolder.mkdir(parents=True, exist_ok=True)
        slug_desoneracao = desoneracao.lower().replace("-", "_")
        filename = f"cub_{ano}_{mes:02d}_{slug_desoneracao}.pdf"
        return subfolder / filename

    def extract(self, source_reference: Any, **kwargs) -> Tuple[Path, bool]:
        """
        Extrai PDF da web ou do cache local.
        Retorna (caminho_arquivo, is_from_cache).
        """
        uf = kwargs.get("uf", "GO")
        sinduscon_id = kwargs.get("sinduscon_id", 10)
        ano = kwargs.get("ano", 2026)
        mes = kwargs.get("mes", 1)
        desoneracao = kwargs.get("desoneracao", "sem-desoneracao")
        force_download = kwargs.get("force_download", False)

        target_path = self.get_cached_pdf_path(uf, sinduscon_id, ano, mes, desoneracao)

        # Cache Hit
        if target_path.exists() and not force_download and target_path.stat().st_size > 1000:
            logger.info(f"[CACHE HIT] Usando arquivo local: {target_path}")
            return target_path, True

        # Cache Miss: download com taxa controlada
        logger.info(f"[CACHE MISS] Baixando do cub.org.br: {uf} / {sinduscon_id} ({ano}-{mes:02d})")
        pdf_bytes = self.client.download_pdf(
            uf=uf,
            sinduscon_id=sinduscon_id,
            ano=ano,
            mes=mes,
            desoneracao=desoneracao
        )

        with open(target_path, "wb") as f:
            f.write(pdf_bytes)

        # Pausa educada ao servidor da CBIC
        sleep_time = self.request_delay + random.uniform(0.3, 1.2)
        logger.debug(f"Pausa de cortesia: {sleep_time:.2f}s")
        time.sleep(sleep_time)

        return target_path, False

    def transform(self, raw_content: Any, **kwargs) -> StandardEtlResult:
        file_path, is_cached = raw_content
        return StandardEtlResult(
            adapter_id=self.adapter_id,
            source_identifier=str(file_path),
            status="SUCCESS",
            records_count=1,
            data=file_path,
            metadata={"is_cached": is_cached}
        )
