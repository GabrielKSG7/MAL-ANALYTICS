# Arquitetura

## Visão geral

```mermaid
flowchart LR
    subgraph Fontes
        MAL[MAL API v2<br/>oficial]
        JK[Jikan v4<br/>não oficial]
        MN[anime-offline-database<br/>GitHub, semanal]
        KG[Kaggle 2020<br/>CSV ~109M linhas]
    end

    subgraph "malpipe (Python)"
        HTTP[PoliteClient<br/>rate limit · retry · Retry-After]
        CK[Checkpoint<br/>derivado do próprio bronze]
    end

    subgraph "DuckDB · data/mal.duckdb"
        BR[(bronze<br/>JSON cru, append-only)]
        ST[staging<br/>views tipadas]
        IN[intermediate<br/>franquias · bayes · polarização]
        CO[core<br/>dims · bridges · fatos]
        AN[analytics<br/>marts]
        SN[snapshots<br/>SCD2]
        ML[ml<br/>recomendações]
    end

    MAL --> HTTP
    JK --> HTTP
    HTTP --> BR
    MN --> BR
    KG -->|read_csv paralelo| BR
    CK -.decide o que extrair.-> HTTP
    BR -.consultado por.-> CK
    BR --> ST --> IN --> CO --> AN
    ST --> SN
    CO --> REC[recsys<br/>kNN · SVD · conteúdo · híbrido] --> ML
    AN --> DASH[Streamlit]
    ML --> DASH
```

## Camadas

| Camada | Materialização | Responsabilidade |
|---|---|---|
| `bronze` | tabelas append-only | O JSON exatamente como veio da API, com status HTTP, horário e `run_id`. Nunca é alterado. |
| `meta` | tabela | `meta.runs`: cada execução do pipeline (comando, início/fim, status, linhas, notas). |
| `staging` | views | Parsing do JSON, tipagem, datas parciais do MAL, "última extração vence". 1 modelo por entidade. |
| `intermediate` | views/tabela | Lógica reutilizável e testável isoladamente (com unit tests): franquias por grafo, nota bayesiana, forma da distribuição de notas, normalização por usuário. |
| `core` | tabelas (+1 incremental) | Modelo dimensional: `dim_anime`, `dim_genre`, `dim_studio`, `dim_person`, `dim_character`, pontes N:N e fatos. |
| `analytics` | tabelas | Uma mart por pergunta de negócio. É o que o dashboard consome. |
| `snapshots` | dbt snapshot | SCD tipo 2 de status de exibição, episódios e título. |
| `ml` | tabelas (Python) | Métricas dos modelos, animes similares e recomendações para a sua lista. |

## Modelo dimensional (core)

```mermaid
erDiagram
    dim_anime ||--o{ bridge_anime_genre : tem
    dim_genre ||--o{ bridge_anime_genre : classifica
    dim_anime ||--o{ bridge_anime_studio : produzido_por
    dim_studio ||--o{ bridge_anime_studio : produz
    dim_anime ||--o{ bridge_anime_cast : elenco
    dim_character ||--o{ bridge_anime_cast : personagem
    dim_person ||--o{ bridge_anime_cast : dublador
    dim_anime ||--o{ fct_anime_metrics_snapshot : "série temporal"
    dim_anime ||--o{ fct_user_rating : avaliado_em
    dim_anime ||--o{ fct_my_list : na_sua_lista
    dim_anime ||--o{ bridge_anime_staff : creditos
    dim_person ||--o{ bridge_anime_staff : trabalhou_em
    dim_anime ||--o{ fct_episode : episodios
    dim_manga ||--o{ bridge_manga_anime : adaptado_em
    dim_anime ||--o{ bridge_manga_anime : adapta
    dim_manga ||--o{ bridge_manga_author : escrito_por

    dim_anime {
        int mal_id PK
        varchar title
        int franchise_id
        double mean_score
        double weighted_score
        double polarization_index
        double completion_rate
        int anilist_id
    }
    fct_anime_metrics_snapshot {
        int mal_id FK
        date snapshot_date
        double mean_score
        bigint num_list_users
    }
    bridge_anime_staff {
        int mal_id FK
        int person_id FK
        varchar role
        varchar role_group
    }
    fct_episode {
        int mal_id FK
        int episode_number
        date aired_on
        int length_min
    }
    dim_manga {
        int manga_id PK
        varchar title
        double mean_score
        bool has_anime_adaptation
        int years_until_adaptation
    }
    fct_user_rating {
        varchar user_key
        int mal_id FK
        int user_score
        double score_z
    }
```

## Fluxo de uma execução semanal (`malpipe incremental`)

1. **manami** — baixa o snapshot semanal; se a `dataset_date` já existe no bronze, não faz nada (idempotente).
2. **descoberta** — varre as temporadas do ano anterior até o próximo (novos títulos e anúncios).
3. **detalhes MAL** — calcula a fila: IDs conhecidos (descobertos + manami) **menos** os extraídos com sucesso
   há menos de `REFRESH_DAYS` **menos** os que já deram 404. Falhas transitórias voltam para a fila.
4. **Jikan** — mesma lógica, para IDs que já têm detalhe do MAL (refresh 4× mais espaçado).
5. **sua lista** — extração completa (é pequena); o staging usa só a mais recente.
6. **dbt build** — o incremental `fct_anime_metrics_snapshot` acrescenta o dia novo; `mart_anime_trending` compara com a semana anterior.
7. **recommend** — retreina e regrava `ml.*`.

Se o processo cair no meio, basta rodar de novo: o que já foi gravado sai da fila automaticamente.

## Por que DuckDB?

Ver [ADR 001](adr/001-duckdb-como-warehouse.md). Em resumo: os ~109M de linhas do Kaggle cabem
num notebook; DuckDB lê CSV/JSON/Parquet nativamente, tem funções de JSON e listas excelentes,
e o projeto roda sem servidor. Migrar para Postgres/BigQuery/Snowflake depois é trocar o adapter do dbt.
