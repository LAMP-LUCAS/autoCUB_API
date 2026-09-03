.PHONY: setup up down populate-db logs-api logs-worker logs-kong status test test-unit test-integration test-e2e test-cov help

help:
	@echo "=========================================================="
	@echo "  AutoCUB API — Automação de Comandos (Make)"
	@echo "=========================================================="
	@echo "  make setup            - Prepara ambiente e gera arquivo .env"
	@echo "  make up               - Sobe containers Docker em background"
	@echo "  make down             - Para containers e limpa volumes"
	@echo "  make populate-db      - Dispara ETL para popular dados do CUB"
	@echo "  make logs-api         - Visualiza logs da API FastAPI"
	@echo "  make logs-worker      - Visualiza logs do worker Celery"
	@echo "  make logs-kong        - Visualiza logs do Kong Gateway"
	@echo "  make status           - Status dos containers"
	@echo "  make test             - Executa todos os testes automatizados"
	@echo "  make test-unit        - Executa apenas testes unitários"
	@echo "  make test-integration - Executa apenas testes de integração"
	@echo "  make test-e2e         - Executa apenas testes ponta a ponta (E2E)"
	@echo "  make test-cov         - Executa testes com relatório de cobertura"
	@echo "=========================================================="

setup:
	@echo Inicializando ambiente AutoCUB...
	@python -c "import os, shutil; shutil.copyfile('.env.example', '.env') if not os.path.exists('.env') else None; print('Arquivo .env pronto com sucesso.')"

up:
	@echo Iniciando containers Docker em modo detached...
	docker compose up --build -d

down:
	@echo Parando e removendo containers, redes e volumes...
	docker compose down -v

populate-db:
	@echo Disparando tarefa de ETL para popular o banco de dados...
	docker compose exec api python -c "from autocub.tasks.etl_tasks import run_etl_pipeline; run_etl_pipeline(ano_inicio=2026, ano_fim=2026, ufs=['GO'])"

logs-api:
	docker compose logs -f api

logs-worker:
	docker compose logs -f celery_worker

logs-kong:
	docker compose logs -f kong

status:
	docker compose ps

test:
	python -m pytest -v

test-unit:
	python -m pytest -v -m unit

test-integration:
	python -m pytest -v -m integration

test-e2e:
	python -m pytest -v -m e2e

test-cov:
	python -m pytest -v --cov=autocub --cov-report=term-missing

