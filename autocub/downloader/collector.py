import os
import time
import random
from pathlib import Path
from typing import Optional
from autocub.core.config import settings
from autocub.core.logging import logger
from autocub.downloader.client import CubHttpClient


class CubCollector:
    """
    Coletor progressivo e ético de relatórios CUB.
    Implementa cache local em disco (DRY com autoSINAPI) e controle de taxa de requisições.
    """

    def __init__(
        self,
        download_dir: Optional[str] = None,
        request_delay: Optional[float] = None
    ):
        self.download_dir = Path(download_dir or settings.CUB_DOWNLOAD_DIR)
        self.request_delay = request_delay or settings.CUB_REQUEST_DELAY_SECONDS
        self.client = CubHttpClient()

    def get_cached_pdf_path(
        self,
        uf: str,
        sinduscon_id: int,
        ano: int,
        mes: int,
        desoneracao: str
    ) -> Path:
        """Gera o caminho padronizado do arquivo PDF em cache local."""
        subfolder = self.download_dir / uf.upper() / str(sinduscon_id)
        subfolder.mkdir(parents=True, exist_ok=True)
        slug_desoneracao = desoneracao.lower().replace("-", "_")
        filename = f"cub_{ano}_{mes:02d}_{slug_desoneracao}.pdf"
        return subfolder / filename

    def collect_pdf(
        self,
        uf: str,
        sinduscon_id: int,
        ano: int,
        mes: int,
        desoneracao: str = "sem-desoneracao",
        force_download: bool = False
    ) -> tuple[Path, bool]:
        """
        Retorna (caminho_arquivo, is_from_cache).
        Se o arquivo já existir em disco e não for forçado, usa o cache local.
        """
        target_path = self.get_cached_pdf_path(uf, sinduscon_id, ano, mes, desoneracao)

        if target_path.exists() and not force_download and target_path.stat().st_size > 1000:
            logger.info(f"[CACHE HIT] Usando arquivo local: {target_path}")
            return target_path, True

        # Cache Miss: faz o download com rate-limiting educado
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

        # Respeito à taxa do servidor CBIC (backoff educado com jitter)
        sleep_time = self.request_delay + random.uniform(0.3, 1.2)
        logger.debug(f"Pausa de cortesia ao servidor: {sleep_time:.2f}s")
        time.sleep(sleep_time)

        return target_path, False
