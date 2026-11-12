# Atalhos do projeto. No Windows, use o equivalente em scripts/tasks.ps1.
SHELL := /bin/bash
# O caminho do banco vem do .env (DUCKDB_PATH); `malpipe dbt` repassa o mesmo caminho para o dbt.
DBT := malpipe dbt

.PHONY: help install demo ingest ecosystem sources site site-preview build publish dbt-build dbt-docs recommend dashboard test lint status clean

help: ## Lista os comandos
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Instala o pacote e as dependências (dev + dashboard)
	pip install -e ".[dev,dashboard]"

demo: ## Ponta a ponta com dados SINTÉTICOS (sem credenciais): bronze → dbt → recomendador
	DUCKDB_PATH=$(CURDIR)/data/demo.duckdb malpipe sample
	DUCKDB_PATH=$(CURDIR)/data/demo.duckdb $(MAKE) dbt-build
	DUCKDB_PATH=$(CURDIR)/data/demo.duckdb malpipe recommend --username demo_user
	@echo "Pronto. Rode: DUCKDB_PATH=$(CURDIR)/data/demo.duckdb make dashboard"

ingest: ## Ingestão incremental real (manami → temporadas → detalhes → Jikan → sua lista)
	malpipe incremental

ecosystem: ## Mangá (MAL) + elenco/staff (AniList) + episódios (Kitsu), em paralelo (~20 h, retomável)
	malpipe check-sources
	malpipe ecosystem

site: ## Atualiza os dados do painel público (site/data) a partir das marts
	malpipe site
	python scripts/check_site.py site

site-preview: ## Abre o painel público localmente em http://localhost:8000
	python -m http.server -d site 8000

sources: ## Testa a conexão com todas as fontes
	malpipe check-sources

build: dbt-build recommend publish site ## dbt build + recomendador + cópia para o DBeaver + dados do painel público

dbt-build: ## Roda modelos, snapshot, testes e unit tests do dbt
	$(DBT) build

dbt-docs: ## Gera e abre a documentação do dbt (lineage)
	$(DBT) docs generate && $(DBT) docs serve --port 8081

publish: ## Atualiza a cópia de consulta (DBeaver/Power BI)
	malpipe publish

recommend: ## Treina/avalia os recomendadores e grava no schema ml
	malpipe recommend

dashboard: ## Abre o dashboard Streamlit
	streamlit run dashboard/app.py

test: ## Testes Python
	pytest

lint: ## Ruff
	ruff check src tests dashboard && ruff format --check src tests dashboard

status: ## Contagens, últimas execuções e fila pendente
	malpipe status

clean: ## Remove artefatos do dbt (não apaga o banco)
	rm -rf dbt/target dbt/logs dbt/dbt_packages
