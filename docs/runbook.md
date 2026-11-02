# Runbook — operando o pipeline

## Primeira carga real (uma vez)

```bash
cp .env.example .env              # preencha MAL_CLIENT_ID e MAL_USERNAME
malpipe init
malpipe manami                    # ~30 mil IDs do MAL em segundos
malpipe discover --seasons 1960-2027   # completa o universo de IDs (≈ 270 chamadas)
malpipe status                    # mostra quantos IDs estão na fila e o tempo estimado
malpipe my-list                   # antes dos detalhes: os animes da sua lista vão para o topo da fila

# carga longa: pode ser feita em partes; o checkpoint retoma de onde parou
malpipe mal-details --limit 5000
malpipe mal-details               # o restante

malpipe jikan statistics          # distribuição de notas (polarização)
malpipe jikan recommendations     # opcional: avaliação externa do recomendador
malpipe jikan characters          # opcional: grafo de dubladores

# Kaggle (ver docs/data-sources.md para o download)
malpipe kaggle data/raw/animelist.csv

make build                        # dbt build + recomendador
make dashboard
```

## Ecossistema: mangá, elenco, staff e episódios (uma vez, ~20 h)

```bash
malpipe check-sources             # testa MAL anime/mangá, AniList, Kitsu, Jikan e manami em segundos
malpipe ecosystem --limit 20      # ensaio: 20 itens de cada fonte (~2 min)
malpipe ecosystem                 # tudo: mangá (MAL) + AniList + Kitsu em paralelo
malpipe status                    # tabela "Ecossistema": concluídos × pendentes por fonte
make build                        # ou .\scripts\tasks.ps1 build
```

- Pode interromper com Ctrl+C a qualquer momento: cada fonte retoma de onde parou.
- Rodar uma fonte só: `malpipe ecosystem --only anilist` (ou `malpipe manga`, `malpipe anilist`, `malpipe kitsu`).
- A AniList prioriza os animes da sua lista; o Kitsu precisa do `malpipe manami` já feito (é dele o mapa de IDs).
- Atualização: depois de `REFRESH_DAYS` (mangá/AniList) ou 4× isso (episódios), os itens voltam para a fila.

> Dica: o Jikan é o gargalo (3 endpoints × 30 mil IDs). Comece só com `statistics`, ou suba uma
> instância local do Jikan, ou limite aos animes com mais membros usando `--limit`.

## Rotina semanal

```bash
malpipe incremental && make build
```

### Agendando no Windows (Agendador de Tarefas)

1. Crie `run_weekly.ps1`:
   ```powershell
   Set-Location "C:\caminho\para\MAL-ANALYTICS"
   .\.venv\Scripts\Activate.ps1
   malpipe incremental
   .\scripts\tasks.ps1 build
   ```
2. Agendador de Tarefas → Criar Tarefa Básica → Semanal → Ação: `powershell.exe`
   com argumentos `-ExecutionPolicy Bypass -File "C:\caminho\run_weekly.ps1"`.

### Agendando no Linux/WSL (cron)

```cron
0 6 * * 1  cd ~/MAL-ANALYTICS && . .venv/bin/activate && malpipe incremental && make build >> data/cron.log 2>&1
```

## Diagnóstico

| Sintoma | Onde olhar | O que fazer |
|---|---|---|
| Muitos 429 | `malpipe status` (notas da execução) e o teste `assert_bronze_not_mostly_errors` | Baixe `MAL_RPS`/`JIKAN_RPS` para 0.5 e rode de novo — a fila retoma sozinha. |
| `HTTP 401/403` no MAL | Client ID | Confira `MAL_CLIENT_ID` no `.env`. |
| `my-list` falha | Privacidade da lista | A lista precisa estar pública no MAL. |
| `dbt source freshness` em WARN | Fonte desatualizada | Rode a ingestão daquela fonte. |
| Banco "travado" (lock) | Outro processo com o DuckDB aberto | Feche o Streamlit/notebook antes de rodar dbt ou ingestão (DuckDB tem um escritor por vez). |
| `AniList rejeitou a consulta` | Erro de GraphQL (schema mudou) | Veja a mensagem no log; a carga para após 3 erros seguidos para não gravar lixo. |
| AniList muito lenta / 429 | Modo degradado (30 req/min) | Normal. Mantenha `ANILIST_RPS=0.45`; o `Retry-After` é respeitado. |
| Kitsu com 0 pendentes | Falta o mapa de IDs | Rode `malpipe manami` e depois `malpipe kitsu`. |
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
