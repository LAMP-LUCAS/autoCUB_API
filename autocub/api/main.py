from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from autocub.core.config import settings
from autocub.core.logging import logger
from autocub.database.connection import init_db, engine
from autocub.api.routers import cub_router, metadata_router, admin_router, kb_router, calc_router





@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando AutoCUB API...")
    try:
        init_db()
        logger.info("Banco de dados inicializado e sementes verificadas.")
    except Exception as e:
        logger.error(f"Aviso na inicialização do banco: {e}")
    yield
    logger.info("Encerrando AutoCUB API...")


TAGS_METADATA = [
    {
        "name": "CUB / Custo Unitário Básico",
        "description": (
            "**Consultas, Cotações e Indicadores:** Endpoints para obtenção de custos do m² residencial, comercial e especial, "
            "CUB Médio Brasil oficial ponderado (21 capitais), painel analítico consolidado (`/dash`), "
            "estudos tributários da CPRB (`/deson`), rankings nacionais (`/rank`) e séries históricas (`/hist`)."
        ),
    },
    {
        "name": "Calculadoras Paramétricas Normativas",
        "description": (
            "**Cálculos de Engenharia (NBR 12.721:2006):** Conversão rigorosa de áreas físicas reais em "
            "Área Equivalente de Construção (Quadro II) e geração automatizada de orçamentos estimativos preliminares."
        ),
    },
    {
        "name": "Base de Conhecimento Perene & Normas",
        "description": (
            "**Inteligência Normativa e Jurídica:** Catálogo dos 29 insumos básicos, itens expressamente não inclusos no CUB "
            "(fundações, elevadores, BDI), fundamentos da Lei Federal 4.591/1964 e súmulas do STJ."
        ),
    },
    {
        "name": "Metadados & Padrões Construtivos",
        "description": (
            "**Padrões da Construção e Sindicatos:** Especificações arquitetônicas dos 19 projetos-padrão normatizados "
            "(áreas, dormitórios, vagas) e catálogo dos 28 Sinduscons com numeração canônica oficial da CBIC."
        ),
    },
    {
        "name": "Administração & ETL",
        "description": (
            "**Operações de Coleta e Auditoria:** Disparo assíncrono do pipeline ETL ético e consulta aos "
            "logs forenses de auditoria de execuções com detalhamento de durações, erros e status de cada relatório."
        ),
    },
    {
        "name": "Health",
        "description": "Monitoramento de integridade, saúde da conexão com o banco PostgreSQL e status do serviço.",
    },
]


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers versionados
app.include_router(metadata_router, prefix=settings.API_PREFIX)
app.include_router(cub_router, prefix=settings.API_PREFIX)
app.include_router(admin_router, prefix=settings.API_PREFIX)
app.include_router(kb_router, prefix=settings.API_PREFIX)
app.include_router(calc_router, prefix=settings.API_PREFIX)



@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_PREFIX}/health", tags=["Health"])
def health_check():
    """
    Health check para balanceadores de carga, Kubernetes e Kong Gateway.
    Verifica a conectividade ativa com a infraestrutura.
    """
    from sqlalchemy import text
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"


    return {
        "status": "online",
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status
    }
