import re
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

from autocub.core.config import settings
from autocub.core.logging import logger
from autocub.core.cache import cache


class CbicDiscoveryService:
    """
    Serviço de descoberta dinâmica de Sinduscons e UFs ativas no portal cub.org.br.
    Evita tentativas de requisições com IDs inválidos ou para estados que não publicam na CBIC.
    """

    BASE_URL = "http://www.cub.org.br/cub-m2-estadual"
    CACHE_PREFIX = "cbic:discovery"
    CACHE_TTL = 604800  # 7 dias de cache em memória/Redis

    # Cache local em memória caso Redis esteja indisponível
    _memory_cache: Dict[str, Dict] = {}

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def inspect_uf(self, uf: str, force_refresh: bool = False) -> Dict:
        """
        Inspeciona a página oficial da UF no cub.org.br e extrai dinamicamente
        os Sinduscons ativos no formulário da CBIC.
        """
        uf_upper = uf.upper()
        cache_key = f"{self.CACHE_PREFIX}:{uf_upper}"

        if not force_refresh:
            # 1. Tenta Redis
            cached = cache.get(cache_key)
            if cached:
                return cached
            # 2. Tenta cache em memória da instância
            if uf_upper in self._memory_cache:
                return self._memory_cache[uf_upper]

        url = f"{self.BASE_URL}/{uf_upper}/"
        try:
            r = requests.get(url, headers=self.headers, timeout=6)
            if r.status_code != 200:
                data = {
                    "uf": uf_upper,
                    "is_supported": False,
                    "status_code": r.status_code,
                    "motivo": f"Servidor CBIC respondeu com status {r.status_code}",
                    "sinduscons": []
                }
                self._save_cache(cache_key, uf_upper, data)
                return data

            soup = BeautifulSoup(r.text, "html.parser")
            sind_select = soup.find("select", {"name": "sinduscon"})

            if not sind_select:
                data = {
                    "uf": uf_upper,
                    "is_supported": False,
                    "status_code": 200,
                    "motivo": "Página não possui formulário de seleção de sinduscon",
                    "sinduscons": []
                }
                self._save_cache(cache_key, uf_upper, data)
                return data

            sinduscons = []
            for opt in sind_select.find_all("option"):
                val = opt.get("value", "").strip()
                nome = opt.text.strip()
                if val and val != "-1":
                    try:
                        sinduscons.append({
                            "id": int(val),
                            "nome": nome,
                            "uf": uf_upper
                        })
                    except ValueError:
                        continue

            is_supported = len(sinduscons) > 0
            motivo = "Ativo no portal nacional CBIC" if is_supported else "Estado não publica no portal central cub.org.br (opção -1=---)"

            data = {
                "uf": uf_upper,
                "is_supported": is_supported,
                "status_code": 200,
                "motivo": motivo,
                "sinduscons": sinduscons
            }
            self._save_cache(cache_key, uf_upper, data)
            return data

        except Exception as e:
            logger.warning(f"Falha ao inspecionar UF {uf_upper} no CBIC: {str(e)}")
            return {
                "uf": uf_upper,
                "is_supported": True,  # Modo conservador: assume suportado se rede oscilar
                "status_code": 0,
                "motivo": f"Erro de conexão: {str(e)}",
                "sinduscons": []
            }

    def _save_cache(self, cache_key: str, uf: str, data: Dict) -> None:
        self._memory_cache[uf] = data
        cache.set(cache_key, data, ttl=self.CACHE_TTL)

    def is_uf_supported(self, uf: str) -> bool:
        """Retorna se o estado integra o portal nacional da CBIC."""
        info = self.inspect_uf(uf)
        return info.get("is_supported", False)

    def get_active_sinduscon_ids(self, uf: str) -> List[int]:
        """Retorna a lista de IDs de Sinduscons válidos para uma UF."""
        info = self.inspect_uf(uf)
        return [s["id"] for s in info.get("sinduscons", [])]

    def validate_or_resolve_sinduscon_id(self, uf: str, requested_id: int) -> Optional[int]:
        """
        Valida se o requested_id é válido na CBIC para a UF.
        Se inválido, mas a UF tiver apenas um sinduscon ativo, resolve automaticamente para o ID correto.
        """
        info = self.inspect_uf(uf)
        if not info.get("is_supported"):
            return None

        active_sinds = info.get("sinduscons", [])
        active_ids = [s["id"] for s in active_sinds]

        if requested_id in active_ids:
            return requested_id

        # Auto-resolução se a UF tem exatamente um Sinduscon ativo oficial
        if len(active_ids) == 1:
            resolved_id = active_ids[0]
            logger.info(
                f"Auto-resolução de Sinduscon: UF={uf} solicitou ID={requested_id}, "
                f"mas o ID oficial CBIC é {resolved_id} ({active_sinds[0]['nome']}). Corrigido dinamicamente."
            )
            return resolved_id

        return None


# Instância global singleton
cbic_discovery = CbicDiscoveryService()
