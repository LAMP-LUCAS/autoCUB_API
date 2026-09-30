from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from autocub.core.config import settings
from autocub.core.logging import logger
from autocub.database.connection import init_db, engine, get_db
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
def health_check(db: Session = Depends(get_db)):
    """
    Health check para balanceadores de carga, Kubernetes e Kong Gateway.
    Verifica a conectividade ativa com a infraestrutura.

    Contrato canônico do ecossistema Mundoaec: `GET /api/v1/cub/health`
    (registrado no router CUB, antes do catch-all `/{uf}`). Mantém `/health`
    e `/v1/health` para probes de container/CI direto no upstream.

    §5.8 (auditoria MCP de custo): `stage` (env `STAGE`, default
    `development`) substitui o antigo `environment`, que reportava
    "development" em produção; `fontes` mapeia UF → sindicatos que
    efetivamente publicaram cotação, para o agente sinalizar a origem.
    """
    from sqlalchemy import text
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # §5.8 (auditoria MCP de custo): fontes por UF — sindicatos que
    # efetivamente publicaram cotação. Derivado de DADO PUBLICADO (não do
    # cadastro): UF sem cotação não aparece no mapa, coerente com a
    # sinalização LIM-38 ("dado ainda não disponibilizado pelo CBIC").
    # Usa a sessão injetada (get_db) — e não o engine global — para que a
    # suíte meça o banco de teste e a produção o banco real. Falha degrada
    # para mapa vazio — health nunca pode virar 500.
    fontes: dict[str, list[str]] = {}
    try:
        rows = db.execute(text(
            "SELECT DISTINCT s.uf, s.nome FROM cub_mensal m "
            "JOIN sinduscons s ON s.id = m.sinduscon_id "
            "ORDER BY s.uf, s.nome"
        )).all()
        for uf_fonte, nome_fonte in rows:
            fontes.setdefault(uf_fonte, []).append(nome_fonte)
    except Exception:
        fontes = {}

    return {
        "status": "online",
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "stage": settings.STAGE,
        "database": db_status,
        "fontes": fontes,
    }
