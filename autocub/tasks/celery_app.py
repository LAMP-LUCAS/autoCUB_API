from autocub.core.config import settings
from autocub.core.logging import logger

try:
    from celery import Celery
    celery_app = Celery(
        "autocub_worker",
        broker=settings.get_redis_url,
        backend=settings.get_redis_url,
        include=["autocub.tasks.etl_tasks"]
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="America/Sao_Paulo",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
    )
except ImportError:
    celery_app = None
    logger.debug("Pacote 'celery' não instalado neste ambiente. Modo standalone/local ativo.")
