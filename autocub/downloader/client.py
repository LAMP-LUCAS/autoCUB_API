import requests
from bs4 import BeautifulSoup
from typing import Optional
from autocub.core.config import settings
from autocub.core.logging import logger


class CubHttpClient:
    """
    Cliente HTTP para interação educada e resiliente com o portal cub.org.br da CBIC.
    Gerencia cookies de sessão e CSRF tokens do Django.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.CUB_BASE_URL
        self.session = requests.Session()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": f"{self.base_url}/cub-m2-estadual/GO/",
        }

    def _get_csrf_token(self, uf: str) -> str:
        """Obtém o CSRF token acessando a página estadual do CUB."""
        url = f"{self.base_url}/cub-m2-estadual/{uf}/"
        response = self.session.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()

        # Tenta pegar do cookie da sessão
        token = self.session.cookies.get("csrftoken")
        if not token:
            soup = BeautifulSoup(response.text, "html.parser")
            inp = soup.find("input", {"name": "csrfmiddlewaretoken"})
            if inp and inp.get("value"):
                token = inp["value"]

        if not token:
            raise ValueError(f"Não foi possível obter CSRF token da página {url}")

        return token

    def download_pdf(
        self,
        uf: str,
        sinduscon_id: int,
        ano: int,
        mes: int,
        desoneracao: str = "sem-desoneracao"
    ) -> bytes:
        """
        Submete formulário POST e retorna os bytes do relatório PDF oficial do CUB.
        """
        token = self._get_csrf_token(uf)
        url_post = f"{self.base_url}/cub-m2-estadual/{uf}/"

        post_data = {
            "csrfmiddlewaretoken": token,
            "uf": uf,
            "sinduscon": str(sinduscon_id),
            "relatorio": "tabela-cub-m2",
            "ano": str(ano),
            "ano_i": str(ano),
            "ano_f": str(ano),
            "mes": str(mes),
            "desoneracao": desoneracao,  # 'sem-desoneracao' ou 'com-desoneracao'
            "variacao": "com-variacao",
            "cimento": "1",
            "projeto": "1",
        }

        logger.info(
            f"Solicitando CUB PDF para UF={uf}, Sinduscon={sinduscon_id}, "
            f"Período={ano}-{mes:02d}, Desoneração={desoneracao}"
        )

        response = self.session.post(url_post, data=post_data, headers=self.headers, timeout=20)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "application/pdf" not in content_type:
            logger.warning(
                f"Resposta de {url_post} não é PDF (Content-Type: {content_type}). "
                f"Status: {response.status_code}. Conteúdo inicial: {response.text[:300]}"
            )
            raise ValueError(
                f"Servidor não retornou PDF para {uf}/{ano}-{mes:02d}. Verifique se o período já foi publicado."
            )

        return response.content
