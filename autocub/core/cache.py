import json
from decimal import Decimal
from datetime import date, datetime
from functools import wraps
from typing import Any, Optional, Callable

try:
    import redis
except ImportError:
    redis = None

from autocub.core.config import settings
from autocub.core.logging import logger



class CustomJSONEncoder(json.JSONEncoder):
    """Encoder para lidar com Decimal, date e datetime na serialização de cache."""
    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if hasattr(o, "model_dump"):
            return o.model_dump()
        return super().default(o)


class CacheService:
    """
    Serviço de cache Redis para armazenar respostas de relações intra-API pré-calculadas.
    Possui tolerância a falhas (fail-open): se o Redis estiver fora, a API continua funcionando.
    """

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
        self._init_connection()

    def _init_connection(self) -> None:
        if not redis:
            self._is_connected = False
            self._client = None
            return
        try:

            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            self._client.ping()
            self._is_connected = True
            logger.info("Cache Redis conectado com sucesso para relações Intra-API.")
        except Exception as e:
            self._is_connected = False
            self._client = None
            logger.warning(f"Redis indisponível ({str(e)}). Operando em modo direto sem cache em memória.")

    def get(self, key: str) -> Optional[Any]:
        if not self._is_connected or not self._client:
            return None
        try:
            data = self._client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug(f"Falha ao ler cache Redis [{key}]: {str(e)}")
        return None

    def set(self, key: str, value: Any, ttl: int = 86400) -> bool:
        if not self._is_connected or not self._client:
            return False
        try:
            serialized = json.dumps(value, cls=CustomJSONEncoder)
            self._client.setex(name=key, time=ttl, value=serialized)
            return True
        except Exception as e:
            logger.debug(f"Falha ao gravar cache Redis [{key}]: {str(e)}")
            return False

    def invalidate(self, pattern: str) -> int:
        """Invalida chaves correspondentes ao padrão (ex: 'cub:dash:GO:*')."""
        if not self._is_connected or not self._client:
            return 0
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
        except Exception as e:
            logger.debug(f"Falha ao invalidar cache Redis [{pattern}]: {str(e)}")
        return 0


# Instância global singleton
cache = CacheService()


def cache_response(ttl: int = 86400, prefix: str = "cub"):
    """
    Decorator para rotas FastAPI. Cacheia o resultado serializado em JSON no Redis.
    Evita sobrecarga e processamento repetitivo de relações analíticas no servidor.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Filtra o objeto db das chaves de cache
            cache_kwargs = {
                k: str(v)
                for k, v in kwargs.items()
                if k not in ("db", "session") and v is not None
            }
            # Monta chave determinística
            kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(cache_kwargs.items()))
            cache_key = f"{prefix}:{func.__name__}:{kwargs_str}"

            # 1. Tenta recuperar do Redis
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # 2. Executa função original
            result = func(*args, **kwargs)

            # 3. Armazena no Redis
            cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper
    return decorator
