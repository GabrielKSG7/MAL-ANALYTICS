-- =====================================================================================
-- MAL Analytics — consultas prontas para o DBeaver
-- Banco: data/mal_reports.duckdb (gerado por `malpipe publish`) — veja docs/dbeaver.md
--
-- Dica no DBeaver: posicione o cursor numa consulta e use Ctrl+Enter para rodar só ela.
-- Os parâmetros estão como valores fixos e comentados com  -- ◀ troque aqui
-- =====================================================================================


-- -------------------------------------------------------------------------------------
-- 0. O que tem no banco
-- -------------------------------------------------------------------------------------
SELECT schema_name AS camada, table_name AS tabela, estimated_size AS linhas_aprox
FROM duckdb_tables()
ORDER BY camada, tabela;


-- =====================================================================================
-- CATÁLOGO
-- =====================================================================================

-- 1. Top 50 de todos os tempos (nota bayesiana: penaliza poucos votos)
SELECT title, media_type, season_year, main_studio_name, genres_label,
       mean_score, round(weighted_score, 2) AS nota_bayesiana, num_list_users AS membros
FROM core.dim_anime
WHERE media_type IN ('tv', 'movie', 'ona')
ORDER BY weighted_score DESC NULLS LAST
LIMIT 50;

-- 2. Top 5 de cada década
SELECT decade AS decada, title, mean_score, num_list_users AS membros
FROM core.dim_anime
WHERE media_type IN ('tv', 'movie') AND weighted_score IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY decade ORDER BY weighted_score DESC) <= 5
ORDER BY decada DESC, mean_score DESC;

-- 3. Buscar um anime pelo nome (japonês ou inglês)
SELECT mal_id, title, title_english, media_type, season_year, mean_score, mal_url
FROM core.dim_anime
WHERE title ILIKE '%frieren%' OR title_english ILIKE '%frieren%'    -- ◀ troque aqui
ORDER BY start_date;

-- 4. Ficha completa de um anime
SELECT *
FROM core.dim_anime
WHERE mal_id = 52991;                                                  -- ◀ troque aqui

-- 5. Gêneros: volume, nota média e audiência
SELECT g.genre_name AS genero,
       count(*)                       AS titulos,
       round(avg(a.mean_score), 2)    AS nota_media,
       round(median(a.mean_score), 2) AS nota_mediana,
       sum(a.num_list_users)          AS membros_somados
FROM core.bridge_anime_genre b
JOIN core.dim_genre g USING (genre_id)
JOIN core.dim_anime a USING (mal_id)
WHERE a.media_type IN ('tv', 'movie', 'ona')
GROUP BY g.genre_name
HAVING count(*) >= 30
ORDER BY nota_media DESC;

-- 6. Pares de gêneros mais comuns (e qual combinação é mais bem avaliada)
SELECT g1.genre_name AS genero_1, g2.genre_name AS genero_2,
       count(*) AS titulos, round(avg(a.mean_score), 2) AS nota_media
FROM core.bridge_anime_genre b1
JOIN core.bridge_anime_genre b2 ON b1.mal_id = b2.mal_id AND b1.genre_id < b2.genre_id
JOIN core.dim_genre g1 ON g1.genre_id = b1.genre_id
JOIN core.dim_genre g2 ON g2.genre_id = b2.genre_id
JOIN core.dim_anime a ON a.mal_id = b1.mal_id
GROUP BY ALL
HAVING count(*) >= 50
ORDER BY titulos DESC
LIMIT 30;

-- 7. Animes em exibição agora, do mais popular para o menos
SELECT a.title, a.main_studio_name, a.num_episodes, a.mean_score, a.num_list_users AS membros,
       s.broadcast_day AS dia_exibicao
FROM core.dim_anime a
LEFT JOIN staging.stg_mal__anime s USING (mal_id)
WHERE a.airing_status = 'currently_airing'
ORDER BY membros DESC;


-- =====================================================================================
-- ESTÚDIOS, TEMPORADAS E FRANQUIAS
-- =====================================================================================

-- 8. Ranking de estúdios (30+ títulos) por várias métricas
SELECT studio_name AS estudio, num_titles AS titulos, first_year AS desde,
       round(median_score, 2) AS mediana, round(vote_weighted_score, 2) AS nota_ponderada,
       round(score_stddev, 2) AS desvio, round(share_titles_8_plus * 100, 1) AS pct_titulos_8_mais,
       total_members AS membros, best_title AS melhor_titulo
FROM analytics.mart_studio_performance
WHERE num_titles >= 30
ORDER BY mediana DESC;

-- 9. Todas as obras de um estúdio
SELECT season_year, title, media_type, mean_score, num_list_users AS membros
FROM core.dim_anime
WHERE main_studio_name = 'Kyoto Animation'                             -- ◀ troque aqui
ORDER BY season_year, start_date;

-- 10. Uma temporada: tudo o que estreou, por popularidade
SELECT title, media_type, main_studio_name, source_material AS origem, mean_score, num_list_users AS membros
FROM core.dim_anime
WHERE season_key = '2023-Q4-fall'                                      -- ◀ troque aqui (ex.: 2026-Q2-spring)
ORDER BY membros DESC;

-- 11. Origem dos animes por ano (tabela dinâmica com PIVOT)
PIVOT (
    SELECT season_year AS ano,
           CASE WHEN source_material = 'original' THEN 'original'
                WHEN source_material IN ('manga', 'web_manga', '4_koma_manga') THEN 'manga'
                WHEN source_material IN ('light_novel', 'web_novel') THEN 'light_novel'
                ELSE 'outras' END AS origem
    FROM core.dim_anime
    WHERE media_type IN ('tv', 'ona') AND season_year BETWEEN 2006 AND 2026
)
ON origem USING count(*)
ORDER BY ano;

-- 12. Inflação de notas por ano de estreia
SELECT season_year AS ano, num_titles AS titulos, avg_score AS media, median_score AS mediana,
       p10_score AS p10, p90_score AS p90
FROM analytics.mart_score_inflation
WHERE season_year >= 1990
ORDER BY ano;

-- 13. Franquias: maiores, mais longas e se melhoraram ou pioraram
SELECT franchise_name AS franquia, num_entries AS entradas, num_tv_entries AS temporadas_tv,
       total_runtime_hours AS horas, first_year AS inicio, last_year AS ultimo,
       first_tv_entry, first_entry_score, latest_tv_entry, latest_entry_score,
       score_change_first_to_latest AS variacao
FROM analytics.mart_franchise_summary
ORDER BY total_members DESC
LIMIT 40;

-- 14. Todas as entradas de uma franquia, em ordem cronológica
SELECT a.start_date, a.title, a.media_type, a.num_episodes, a.mean_score
FROM core.dim_anime a
WHERE a.franchise_id = (SELECT franchise_id FROM core.dim_anime WHERE title = 'Shingeki no Kyojin')  -- ◀
ORDER BY a.start_date;

-- 15. Joias escondidas (nota alta, pouca gente viu)
SELECT title, media_type, season_year, main_studio_name, genres_label, mean_score,
       num_list_users AS membros, mal_url
FROM analytics.mart_hidden_gems
ORDER BY mean_score DESC;


-- =====================================================================================
-- MINHA LISTA
-- =====================================================================================

-- 16. Resumo da minha lista
SELECT list_status AS status, count(*) AS titulos,
       round(sum(hours_watched)) AS horas, round(avg(user_score), 2) AS minha_media,
       round(avg(mal_mean_score), 2) AS media_mal
FROM core.fct_my_list
GROUP BY ALL
ORDER BY titulos DESC;

-- 17. O que ver primeiro do meu plan-to-watch (mais bem avaliado e mais curto)
SELECT m.title, a.media_type, a.num_episodes, a.total_runtime_hours AS horas,
       a.mean_score, a.genres_label, a.mal_url
FROM core.fct_my_list m
JOIN core.dim_anime a USING (mal_id)
WHERE m.list_status = 'plan_to_watch' AND a.airing_status = 'finished_airing'
ORDER BY a.weighted_score DESC
LIMIT 50;

-- 18. Para um fim de semana: plan-to-watch com até 6 horas, ordenado pela nota
SELECT m.title, a.media_type, a.total_runtime_hours AS horas, a.mean_score
FROM core.fct_my_list m
JOIN core.dim_anime a USING (mal_id)
WHERE m.list_status = 'plan_to_watch' AND a.total_runtime_hours <= 6               -- ◀ horas
ORDER BY a.mean_score DESC
LIMIT 30;

-- 19. Onde eu discordo da comunidade (maiores diferenças nos dois sentidos)
(SELECT 'eu gosto mais' AS lado, title, user_score, mal_mean_score, score_delta
 FROM core.fct_my_list WHERE user_score IS NOT NULL ORDER BY score_delta DESC LIMIT 15)
UNION ALL
(SELECT 'o MAL gosta mais', title, user_score, mal_mean_score, score_delta
 FROM core.fct_my_list WHERE user_score IS NOT NULL ORDER BY score_delta ASC LIMIT 15);

-- 20. Meu perfil vs MAL por gênero/estúdio/década/formato
SELECT dimension AS recorte, value AS valor, num_titles AS titulos,
       my_avg_score AS minha_media, mal_avg_score AS media_mal, delta_avg AS diferenca
FROM analytics.mart_my_profile_vs_mal
WHERE num_titles >= 5
ORDER BY recorte, diferenca DESC;

-- 21. Quanto eu assisti por ano e mês
SELECT year(finished_on) AS ano, month(finished_on) AS mes,
       count(*) AS titulos, round(sum(hours_watched)) AS horas
FROM core.fct_my_list
WHERE finished_on IS NOT NULL
GROUP BY ALL
ORDER BY ano, mes;

-- 22. Estúdios que eu mais assisto (e como avalio cada um)
SELECT main_studio_name AS estudio, count(*) AS titulos,
       round(avg(user_score), 2) AS minha_media, round(avg(mal_mean_score), 2) AS media_mal
FROM core.fct_my_list
WHERE list_status = 'completed' AND main_studio_name IS NOT NULL
GROUP BY ALL
HAVING count(*) >= 3
ORDER BY titulos DESC;

-- 23. Tags temáticas mais comuns entre os animes que dei 9 ou 10
SELECT t.tag, count(*) AS titulos
FROM core.fct_my_list m
JOIN staging.stg_manami__anime_tags t USING (mal_id)
WHERE m.user_score >= 9
GROUP BY t.tag
ORDER BY titulos DESC
LIMIT 30;

-- 24. Minhas recomendações (com o motivo)
SELECT r.rank, r.title, r.because_you_liked AS porque_voce_gostou_de,
       r.already_in_plan_to_watch AS ja_no_ptw, a.mean_score, a.genres_label
FROM ml.recommendations_for_user r
JOIN core.dim_anime a USING (mal_id)
ORDER BY r.model, r.rank
LIMIT 50;


-- =====================================================================================
-- HISTÓRICO E PIPELINE
-- =====================================================================================

-- 25. Evolução semanal de um anime (nota, rank e membros) — cresce a cada extração
SELECT snapshot_date, mean_score, score_rank, popularity_rank, num_list_users AS membros
FROM core.fct_anime_metrics_snapshot
WHERE mal_id = 52991                                                    -- ◀ troque aqui
ORDER BY snapshot_date;

-- 26. Mudanças de status registradas no snapshot (ex.: quando estreou, quando terminou)
SELECT title, airing_status, num_episodes, dbt_valid_from AS desde, dbt_valid_to AS ate
FROM snapshots.snap_anime_status
WHERE mal_id IN (SELECT mal_id FROM snapshots.snap_anime_status GROUP BY 1 HAVING count(*) > 1)
ORDER BY title, desde;

-- 27. Execuções do pipeline
SELECT command AS comando, started_at AS inicio, finished_at AS fim, status,
       rows_written AS linhas, notes AS notas
FROM meta.runs
ORDER BY started_at DESC
LIMIT 30;
