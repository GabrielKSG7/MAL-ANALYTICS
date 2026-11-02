# Consultando os dados no DBeaver

O projeto guarda tudo em arquivos **DuckDB**. O DBeaver abre esse arquivo direto, sem servidor e sem
importação: é só apontar para ele.

## Por que existe uma "cópia de consulta"

O DuckDB aceita **um único processo escrevendo** no arquivo. Se o DBeaver ficar conectado ao banco
principal (`data/mal.duckdb`), a ingestão e o `dbt build` falham com *"Could not set lock on file"*.

Por isso o comando `malpipe publish` gera uma cópia só para consulta:

| Arquivo | Para quê | Quem escreve |
|---|---|---|
| `data/mal.duckdb` | banco de trabalho do pipeline | `malpipe` e dbt |
| `data/mal_reports.duckdb` | **DBeaver, Power BI, Excel** | só o `malpipe publish` |

A cópia traz todas as camadas (staging, intermediate, core, analytics, snapshots, ml, meta) como
tabelas. O bronze, com o JSON cru, fica de fora por padrão (`--include-bronze` para incluir).
O `.\scripts\tasks.ps1 build` já roda o `publish` no final.

```powershell
malpipe publish            # gera/atualiza data\mal_reports.duckdb
```

> Se o DBeaver estiver conectado à cópia na hora do `publish`, o Windows não deixa substituir o
> arquivo. O comando avisa: é só clicar em **Desconectar** no DBeaver e rodar de novo.

## Configurar a conexão (uma vez)

1. **Database → New Database Connection** → procure **DuckDB** → Next.
2. Em **Path**, clique em *Open…* e escolha
   `...\MAL-ANALYTICS\data\mal_reports.duckdb`.
3. Na primeira vez, o DBeaver oferece **baixar o driver** → *Download*.
4. Aba **General** (ou *Connection settings → General*): dê o nome `MAL Analytics` e marque
   **Read-only connection**.
5. **Test Connection** → **Finish**.

### Se aparecer erro de versão ao abrir o arquivo

Mensagens como *"file was written by a newer version"* ou *"Serialization Error"* significam que o driver
do DBeaver é mais antigo que o DuckDB do Python que criou o arquivo.

1. Veja a versão usada pelo projeto: `python -c "import duckdb; print(duckdb.__version__)"`.
2. No DBeaver: **Database → Driver Manager → DuckDB → Edit → Libraries**. Clique em
   **Download/Update** e escolha a mesma versão (ou a mais nova). Depois, **Reconnect**.

## Consultas prontas

Abra `sql/consultas_dbeaver.sql` no DBeaver (**File → Open File**, ou arraste o arquivo). Com o cursor
dentro de uma consulta, **Ctrl+Enter** roda só ela. Valores que você vai querer trocar estão marcados
com `-- ◀ troque aqui`.

| # | Consulta |
|---|---|
| 0 | O que tem no banco (tabelas e tamanho) |
| 1–7 | Catálogo: top 50, top por década, busca por nome, ficha completa, gêneros, pares de gêneros, em exibição |
| 8–15 | Estúdios, uma temporada, origem por ano (PIVOT), inflação, franquias, joias escondidas |
| 16–24 | Minha lista: resumo, **o que ver primeiro do plan-to-watch**, maratona de fim de semana, divergências, perfil, horas por mês, estúdios, tags dos favoritos, recomendações |
| 25–27 | Histórico semanal de um anime, mudanças de status (SCD2) e execuções do pipeline |

O CI do projeto roda todas essas consultas a cada push, então elas continuam válidas quando os modelos mudam.

## Onde ficam os dados (mapa rápido)

| Schema | O que tem | Comece por |
|---|---|---|
| `core` | modelo dimensional | `dim_anime` (1 linha por anime, ~50 colunas), `fct_my_list`, `bridge_anime_genre` |
| `analytics` | uma tabela por pergunta | `mart_studio_performance`, `mart_season_trends`, `mart_my_profile_vs_mal` |
| `ml` | saídas do recomendador | `recommendations_for_user`, `similar_anime` |
| `staging` | dados limpos de cada fonte | `stg_manami__anime_tags` (tags temáticas) |
| `snapshots` | histórico de mudanças (SCD2) | `snap_anime_status` |
| `meta` | execuções do pipeline | `runs` |

Descrição de cada coluna: [data-dictionary.md](data-dictionary.md) ou `make dbt-docs`.

## Dicas para relatórios

- **Gêneros** estão em duas formas: a lista `genres` (para `list_contains(genres, 'Drama')`) e a ponte
  `core.bridge_anime_genre` (para `GROUP BY` por gênero).
- **Nota**: `mean_score` é a média do MAL; `weighted_score` é a nota bayesiana, melhor para rankings
  porque não deixa título com 50 votos ficar no topo.
- **Temporadas**: use `season_key` (`2024-Q4-fall`), que ordena corretamente como texto.
- **Exportar**: no DBeaver, clique com o direito no resultado → *Export data* (CSV, Excel, Parquet…).
  Pela linha de comando, `malpipe export` gera CSVs das principais tabelas.
- **Power BI / Excel**: conectam via ODBC do DuckDB, ou use os CSVs do `malpipe export`.
