import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from autocub.database.models import Base
from autocub.database.connection import get_db
from autocub.database.seed_data import seed_initial_data
from autocub.api.main import app

# Banco de dados de teste SQLite em memória
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session")
def sample_pdf_path() -> Path:
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "docs" / "Exemplos" / "2026-1-Tabela-CUB-m2-variacao-percentual[Publicado].pdf"
    assert pdf_path.exists(), f"PDF de amostra não encontrado em {pdf_path}"
    return pdf_path


@pytest.fixture(scope="function")
def db_session():
    """Gera uma sessão de banco limpa e isolada por teste com seed inicial."""
    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    seed_initial_data(session)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def api_client(db_session):
    """Cliente de teste FastAPI com banco mock injetado."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
