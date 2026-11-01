# Atalhos do projeto. No Windows, use o equivalente em scripts/tasks.ps1.
SHELL := /bin/bash
export DUCKDB_PATH ?= $(CURDIR)/data/mal.duckdb
export DBT_PROFILES_DIR := $(CURDIR)/dbt
DBT := cd dbt && dbt

.PHONY: help install demo ingest build dbt-build dbt-docs recommend dashboard test lint status clean

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

build: dbt-build recommend ## dbt build + recomendador

dbt-build: ## Roda modelos, snapshot, testes e unit tests do dbt
	$(DBT) build

dbt-docs: ## Gera e abre a documentação do dbt (lineage)
	$(DBT) docs generate && $(DBT) docs serve --port 8081

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
