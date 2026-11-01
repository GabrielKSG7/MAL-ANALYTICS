# Runbook — operando o pipeline

## Primeira carga real (uma vez)

```bash
cp .env.example .env              # preencha MAL_CLIENT_ID e MAL_USERNAME
malpipe init
malpipe manami                    # ~30 mil IDs do MAL em segundos
malpipe discover --seasons 1960-2027   # completa o universo de IDs (≈ 270 chamadas)
malpipe status                    # mostra quantos IDs estão na fila e o tempo estimado

# carga longa: pode ser feita em partes; o checkpoint retoma de onde parou
malpipe mal-details --limit 5000
malpipe mal-details               # o restante

malpipe jikan statistics          # distribuição de notas (polarização)
malpipe jikan recommendations     # opcional: avaliação externa do recomendador
malpipe jikan characters          # opcional: grafo de dubladores
malpipe my-list

# Kaggle (ver docs/data-sources.md para o download)
malpipe kaggle data/raw/animelist.csv

make build                        # dbt build + recomendador
make dashboard
```

> Dica: o Jikan é o gargalo (3 endpoints × 30 mil IDs). Comece só com `statistics`, ou suba uma
> instância local do Jikan, ou limite aos animes com mais membros usando `--limit`.

## Rotina semanal

```bash
malpipe incremental && make build
```

### Agendando no Windows (Agendador de Tarefas)

1. Crie `run_weekly.ps1`:
   ```powershell
   Set-Location "C:\caminho\para\mal-anime-analytics"
   .\.venv\Scripts\Activate.ps1
   malpipe incremental
   .\scripts\tasks.ps1 build
   ```
2. Agendador de Tarefas → Criar Tarefa Básica → Semanal → Ação: `powershell.exe`
   com argumentos `-ExecutionPolicy Bypass -File "C:\caminho\run_weekly.ps1"`.

### Agendando no Linux/WSL (cron)

```cron
0 6 * * 1  cd ~/mal-anime-analytics && . .venv/bin/activate && malpipe incremental && make build >> data/cron.log 2>&1
```

## Diagnóstico

| Sintoma | Onde olhar | O que fazer |
|---|---|---|
| Muitos 429 | `malpipe status` (notas da execução) e o teste `assert_bronze_not_mostly_errors` | Baixe `MAL_RPS`/`JIKAN_RPS` para 0.5 e rode de novo — a fila retoma sozinha. |
| `HTTP 401/403` no MAL | Client ID | Confira `MAL_CLIENT_ID` no `.env`. |
| `my-list` falha | Privacidade da lista | A lista precisa estar pública no MAL. |
| `dbt source freshness` em WARN | Fonte desatualizada | Rode a ingestão daquela fonte. |
| Banco "travado" (lock) | Outro processo com o DuckDB aberto | Feche o Streamlit/notebook antes de rodar dbt ou ingestão (DuckDB tem um escritor por vez). |
| Quero reprocessar tudo do zero | — | `dbt build --full-refresh`. O bronze não muda; não há nova chamada às APIs. |

## Consultas úteis

```sql
-- execuções recentes
SELECT command, started_at, status, rows_written, notes FROM meta.runs ORDER BY started_at DESC LIMIT 10;

-- taxa de erro por status HTTP na última semana
SELECT http_status, count(*) FROM bronze.mal_anime
WHERE extracted_at > now() - INTERVAL 7 DAY GROUP BY 1 ORDER BY 2 DESC;

-- quando um anime mudou de status (snapshot SCD2)
SELECT mal_id, title, airing_status, dbt_valid_from, dbt_valid_to
FROM snapshots.snap_anime_status WHERE mal_id = 52991 ORDER BY dbt_valid_from;
```
