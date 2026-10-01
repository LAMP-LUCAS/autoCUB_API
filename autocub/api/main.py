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

    # STORY-MCP-007/C-02: a lacuna de cobertura precisa ficar VISÍVEL antes de
    # o cliente descobrir (o relatório original só a viu Asking por UF). O
    # `status` continua "online" — cobertura é informação de negócio, não
    # falha de serviço.
    cobertura: dict = {}
    try:
        from autocub.api.lim38 import BR_UFS

        ufs_com_dado = sorted(fontes)
        ultima = db.execute(text("SELECT MAX(data_referencia) FROM cub_mensal")).scalar()
        # UF com sindicato cadastrado mas SEM cotação não é a mesma coisa que
        # UF sem cadastro (ex.: RO/SE) — a causa é outra e a correção também.
        registradas = {
            uf for (uf,) in db.execute(text("SELECT DISTINCT uf FROM sinduscons")).all()
        }
        cobertura = {
            "ufs_com_dado": len(ufs_com_dado),
            "ufs_total": len(BR_UFS),
            "ufs_sem_dado": sorted(BR_UFS - set(ufs_com_dado)),
            "ufs_com_sindicado_sem_cotacao": sorted(set(ufs_com_dado) - registradas) or [],
            "ultima_atualizacao": (
                f"{ultima:%Y-%m-%d}" if hasattr(ultima, "year") else (ultima or None)
            ),
        }
        # STORY-MCP-007/B-01: séries com valor repetido (forward-fill). A
        # detecção roda sobre as séries carregadas — é a mesma do detector de
        # ingestão (autocub.processor.repeticao), então o que o health declara é
        # exatamente o que a próxima execução sinalizaria.
        try:
            from autocub.database.models import CubMensal, Sinduscon
            from autocub.processor.repeticao import detectar_repeticoes

            # `db.query(A, B)` devolve TUPLAS — desempacota por posição.
            registros = [
                {"uf": uf, "codigo_padrao": m.codigo_padrao,
                 "desoneracao": m.desoneracao, "data_referencia": m.data_referencia,
                 "valor_m2": m.valor_m2, "variacao_mensal_pct": m.variacao_mensal_pct}
                for uf, m in db.query(Sinduscon.uf, CubMensal).join(
                    CubMensal, CubMensal.sinduscon_id == Sinduscon.id
                ).all()
            ]
            estaveis = detectar_repeticoes(registros)
            # Detalhe por (padrão/desoneração) com as COMPETÊNCIAS afetadas: é o
            # que permite ao MCP marcar a cotação exata no caminho de leitura
            # (STORY-MCP-007 P0-1 — o aviso precisa viajar com o dado).
            por_uf: dict = {}
            for registro in estaveis:
                uf = registro["uf"]
                chave = f"{registro['codigo_padrao']}/{registro['desoneracao']}"
                info = por_uf.setdefault(uf, {
                    "series": {}, "competencias": 0,
                    "fato": "INDICE_MANTIDO_ENTRE_COMPETENCIAS",
                })
                info["competencias"] += 1
                serie = info["series"].setdefault(
                    chave,
                    {"competencias_mantidas": [],
                     "meses_mantido": registro.get("meses_mantido")},
                )
                competencia = str(registro.get("data_referencia") or "")[:7]
                if competencia and competencia not in serie["competencias_mantidas"]:
                    serie["competencias_mantidas"].append(competencia)
            if por_uf:
                # FATO, sem veredito (2026-10-01): o índice foi MANTIDO entre
                # competências — verificado contra a fonte oficial (cub.org.br,
                # 2026-10-01), é o valor que o Sinduscon-AM publica. Isto é
                # diagnóstico de operador; nenhuma resposta de tool desacredita
                # o valor (decisão do usuário: marcar "provisório" injectava
                # desconfiança em dado oficial correto).
                cobertura["series_indice_estavel"] = {
                    "ufs": sorted(por_uf),
                    "total_competencias": len(estaveis),
                    "fato": "INDICE_MANTIDO_ENTRE_COMPETENCIAS",
                    "detalhe": {
                        uf: {**info, "series": sorted(info["series"])}
                        for uf, info in por_uf.items()
                    },
                    "nota": (
                        "Valor oficial mantido entre competências consecutivas "
                        "— confirmado na fonte oficial, não é falha de carga nem "
                        "estimativa. Confira a data de publicação da fonte."
                    ),
                }
        except Exception as exc:  # noqa: BLE001 - health nunca quebra
            cobertura.setdefault("series_indice_estavel", {})

        # B-07: por que cada UF está sem dado e quando sai (roadmap declarado,
        # para o cliente não achar que é falha temporária de consulta).
        from autocub.api.roadmap import roadmap_uf

        cobertura["detalhe_ufs_sem_dado"] = {
            uf: roadmap_uf(db, uf) for uf in cobertura.get("ufs_sem_dado", [])
        }
    except Exception:
        cobertura = {}

    return {
        "status": "online",
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "stage": settings.STAGE,
        "database": db_status,
        "fontes": fontes,
        "cobertura": cobertura,
    }
