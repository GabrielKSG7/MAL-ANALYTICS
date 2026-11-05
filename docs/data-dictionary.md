# Dicionário de dados

> Gerado automaticamente por `scripts/gen_data_dictionary.py` a partir do manifest/catalog do dbt.

## staging

### `staging.stg_anilist__characters` · view

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `character_id` | INTEGER |  |
| `character_name` | VARCHAR |  |
| `character_name_native` | VARCHAR |  |
| `gender` | VARCHAR |  |
| `age` | VARCHAR |  |
| `favourites` | INTEGER |  |
| `image_url` | VARCHAR |  |
| `profile_url` | VARCHAR |  |
| `character_role` | VARCHAR |  |

### `staging.stg_anilist__media` · table

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `anilist_id` | INTEGER |  |
| `title_romaji` | VARCHAR |  |
| `title_english` | VARCHAR |  |
| `title_native` | VARCHAR |  |
| `anilist_favourites` | INTEGER |  |
| `anilist_average_score` | INTEGER |  |
| `anilist_popularity` | INTEGER |  |
| `country_of_origin` | VARCHAR |  |
| `cast_truncated` | BOOLEAN |  |
| `extracted_at` | TIMESTAMP |  |
| `_characters` | STRUCT("role" VARCHAR, node STRUCT(id INTEGER, "name" STRUCT("full" VARCHAR, native VARCHAR), gender VARCHAR, age VARCHAR, favourites INTEGER, image STRUCT(medium VARCHAR), siteUrl VARCHAR), voiceActorRoles STRUCT(roleNotes VARCHAR, dubGroup VARCHAR, voiceActor STRUCT(id INTEGER, "name" STRUCT("full" VARCHAR, native VARCHAR), languageV2 VARCHAR, gender VARCHAR, favourites INTEGER, primaryOccupations VARCHAR[], homeTown VARCHAR, yearsActive INTEGER[], dateOfBirth STRUCT("year" INTEGER, "month" INTEGER, "day" INTEGER), dateOfDeath STRUCT("year" INTEGER, "month" INTEGER, "day" INTEGER), image STRUCT(medium VARCHAR), siteUrl VARCHAR))[])[] |  |
| `_staff` | STRUCT("role" VARCHAR, node STRUCT(id INTEGER, "name" STRUCT("full" VARCHAR, native VARCHAR), languageV2 VARCHAR, gender VARCHAR, favourites INTEGER, primaryOccupations VARCHAR[], homeTown VARCHAR, yearsActive INTEGER[], dateOfBirth STRUCT("year" INTEGER, "month" INTEGER, "day" INTEGER), dateOfDeath STRUCT("year" INTEGER, "month" INTEGER, "day" INTEGER), image STRUCT(medium VARCHAR), siteUrl VARCHAR))[] |  |
| `_studios` | STRUCT(isMain BOOLEAN, node STRUCT(id INTEGER, "name" VARCHAR, isAnimationStudio BOOLEAN, favourites INTEGER, siteUrl VARCHAR))[] |  |
| `_tags` | STRUCT("name" VARCHAR, rank INTEGER, category VARCHAR, isMediaSpoiler BOOLEAN)[] |  |

### `staging.stg_anilist__people` · view

| coluna | tipo | descrição |
|---|---|---|
| `person_id` | INTEGER |  |
| `person_name` | VARCHAR |  |
| `person_name_native` | VARCHAR |  |
| `language` | VARCHAR |  |
| `gender` | VARCHAR |  |
| `favourites` | INTEGER |  |
| `occupations` | VARCHAR[] |  |
| `home_town` | VARCHAR |  |
| `birth_date` | DATE |  |
| `death_date` | DATE |  |
| `active_since` | INTEGER |  |
| `image_url` | VARCHAR |  |
| `profile_url` | VARCHAR |  |

### `staging.stg_anilist__relations` · view

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `relation_type` | VARCHAR |  |
| `related_type` | VARCHAR |  |
| `related_format` | VARCHAR |  |
| `related_anilist_id` | INTEGER |  |
| `related_mal_id` | INTEGER |  |

### `staging.stg_anilist__staff_roles` · view

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `person_id` | INTEGER |  |
| `role` | VARCHAR |  |
| `role_base` | VARCHAR |  |
| `role_group` | VARCHAR |  |

### `staging.stg_anilist__studios` · view

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `anilist_studio_id` | INTEGER |  |
| `studio_name` | VARCHAR |  |
| `is_animation_studio` | BOOLEAN |  |
| `is_main` | BOOLEAN |  |
| `favourites` | INTEGER |  |

### `staging.stg_anilist__tags` · view

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `tag` | VARCHAR |  |
| `category` | VARCHAR |  |
| `relevance` | INTEGER |  |
| `is_spoiler` | BOOLEAN |  |

### `staging.stg_anilist__voice_actors` · view

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `character_id` | INTEGER |  |
| `person_id` | INTEGER |  |
| `voice_language` | VARCHAR |  |
| `role_notes` | VARCHAR |  |
| `dub_group` | VARCHAR |  |

### `staging.stg_jikan__characters` · view

Personagens e dubladores por anime (uma linha por anime × personagem × dublador).

Testes: `accepted_values(character_role)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `character_id` | INTEGER |  |
| `character_name` | VARCHAR |  |
| `character_role` | VARCHAR |  |
| `character_favorites` | INTEGER |  |
| `person_id` | INTEGER |  |
| `person_name` | VARCHAR |  |
| `voice_language` | VARCHAR |  |

### `staging.stg_jikan__recommendations` · view

Pares (anime → anime recomendado) votados pela comunidade.

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `recommended_mal_id` | INTEGER |  |
| `recommended_title` | VARCHAR |  |
| `votes` | INTEGER |  |

### `staging.stg_jikan__score_distribution` · view

Votos por nota (1–10) de cada anime. Permite medir dispersão/polarização, que a média esconde.

Testes: `assert_score_distribution_sums_to_100`, `unique_combination`, `value_between(votes)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `score` | INTEGER |  |
| `votes` | BIGINT |  |
| `percentage` | DOUBLE |  |
| `extracted_at` | TIMESTAMP |  |

### `staging.stg_kaggle__animelist` · view

Interações usuário × anime (Kaggle, 2020) com usuário pseudonimizado.

Testes: `accepted_values(list_status)`, `not_null(user_key)`, `value_between(user_score)`

| coluna | tipo | descrição |
|---|---|---|
| `user_key` | VARCHAR | md5 do user_id original — não expomos o ID do dataset. |
| `mal_id` | INTEGER |  |
| `user_score` | INTEGER |  |
| `status_code` | INTEGER |  |
| `list_status` | VARCHAR |  |
| `episodes_watched` | INTEGER |  |
| `source_file` | VARCHAR |  |

### `staging.stg_kitsu__episodes` · view

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `kitsu_id` | INTEGER |  |
| `episode_number` | INTEGER |  |
| `season_number` | INTEGER |  |
| `relative_number` | INTEGER |  |
| `episode_title` | VARCHAR |  |
| `aired_on` | DATE |  |
| `length_min` | INTEGER |  |
| `synopsis` | VARCHAR |  |

### `staging.stg_mal__anime` · view

Estado atual de cada anime (extração mais recente). Uma linha por mal_id.

Testes: `accepted_values(airing_status)`, `accepted_values(media_type)`, `assert_status_counts_consistent`, `not_null(mal_id)`, `not_null(title)`, `relationships(mal_id)`, `unique(mal_id)`, `value_between(mean_score)`, `value_between(num_list_users)`, `value_between(season_year)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER | ID do anime no MyAnimeList. |
| `extracted_at` | TIMESTAMP |  |
| `snapshot_date` | DATE |  |
| `title` | VARCHAR |  |
| `title_english` | VARCHAR |  |
| `title_japanese` | VARCHAR |  |
| `synopsis` | VARCHAR |  |
| `background` | VARCHAR |  |
| `picture_url_large` | VARCHAR |  |
| `picture_url` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `airing_status` | VARCHAR |  |
| `num_episodes` | INTEGER |  |
| `episode_duration_sec` | INTEGER |  |
| `source_material` | VARCHAR |  |
| `age_rating` | VARCHAR |  |
| `nsfw_level` | VARCHAR |  |
| `start_date_raw` | VARCHAR |  |
| `start_date` | DATE |  |
| `start_date_precision` | VARCHAR | Precisão original da data de início (day, month, year) — o MAL aceita datas parciais. |
| `end_date` | DATE |  |
| `season_year` | INTEGER |  |
| `season_name` | VARCHAR |  |
| `broadcast_day` | VARCHAR |  |
| `broadcast_time_jst` | VARCHAR |  |
| `mean_score` | DOUBLE | Nota média no MAL (1–10). Nula quando ainda não há votos suficientes. |
| `score_rank` | INTEGER |  |
| `popularity_rank` | INTEGER |  |
| `num_list_users` | BIGINT | Membros: quantos usuários têm o anime na lista (qualquer status). |
| `num_scoring_users` | BIGINT |  |
| `status_watching` | BIGINT |  |
| `status_completed` | BIGINT |  |
| `status_on_hold` | BIGINT |  |
| `status_dropped` | BIGINT |  |
| `status_plan_to_watch` | BIGINT |  |
| `mal_created_at` | TIMESTAMP WITH TIME ZONE |  |
| `mal_updated_at` | TIMESTAMP WITH TIME ZONE |  |

### `staging.stg_mal__anime_extractions` · table

Todas as extrações bem-sucedidas de /anime/{id}, tipadas. Base do histórico de métricas.

Testes: `not_null(mal_id)`, `value_between(mean_score)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `extracted_at` | TIMESTAMP |  |
| `snapshot_date` | DATE |  |
| `title` | VARCHAR |  |
| `title_english` | VARCHAR |  |
| `title_japanese` | VARCHAR |  |
| `synopsis` | VARCHAR |  |
| `background` | VARCHAR |  |
| `picture_url_large` | VARCHAR |  |
| `picture_url` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `airing_status` | VARCHAR |  |
| `num_episodes` | INTEGER |  |
| `episode_duration_sec` | INTEGER |  |
| `source_material` | VARCHAR |  |
| `age_rating` | VARCHAR |  |
| `nsfw_level` | VARCHAR |  |
| `start_date_raw` | VARCHAR |  |
| `start_date` | DATE |  |
| `start_date_precision` | VARCHAR |  |
| `end_date` | DATE |  |
| `season_year` | INTEGER |  |
| `season_name` | VARCHAR |  |
| `broadcast_day` | VARCHAR |  |
| `broadcast_time_jst` | VARCHAR |  |
| `mean_score` | DOUBLE |  |
| `score_rank` | INTEGER |  |
| `popularity_rank` | INTEGER |  |
| `num_list_users` | BIGINT |  |
| `num_scoring_users` | BIGINT |  |
| `status_watching` | BIGINT |  |
| `status_completed` | BIGINT |  |
| `status_on_hold` | BIGINT |  |
| `status_dropped` | BIGINT |  |
| `status_plan_to_watch` | BIGINT |  |
| `mal_created_at` | TIMESTAMP WITH TIME ZONE |  |
| `mal_updated_at` | TIMESTAMP WITH TIME ZONE |  |
| `_genres` | STRUCT(id INTEGER, "name" VARCHAR)[] |  |
| `_studios` | STRUCT(id INTEGER, "name" VARCHAR)[] |  |
| `_related_anime` | STRUCT(node STRUCT(id INTEGER, title VARCHAR), relation_type VARCHAR)[] |  |

### `staging.stg_mal__anime_genres` · view

Gêneros, temas e demografias de cada anime (o MAL mistura os três no mesmo campo).

Testes: `relationships(mal_id)`, `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `genre_id` | INTEGER |  |
| `genre_name` | VARCHAR |  |

### `staging.stg_mal__anime_relations` · view

Arestas do grafo de relações (sequel, prequel, side_story...). Base para as franquias.

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `related_mal_id` | INTEGER |  |
| `related_title` | VARCHAR |  |
| `relation_type` | VARCHAR |  |

### `staging.stg_mal__anime_studios` · view

Estúdios de animação de cada anime; is_main_studio marca o primeiro listado.

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `studio_id` | INTEGER |  |
| `studio_name` | VARCHAR |  |
| `is_main_studio` | BOOLEAN |  |

### `staging.stg_mal__manga` · table

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `title_english` | VARCHAR |  |
| `title_japanese` | VARCHAR |  |
| `picture_url` | VARCHAR |  |
| `synopsis` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `publishing_status` | VARCHAR |  |
| `start_date` | DATE |  |
| `end_date` | DATE |  |
| `num_volumes` | INTEGER |  |
| `num_chapters` | INTEGER |  |
| `mean_score` | DOUBLE |  |
| `score_rank` | INTEGER |  |
| `popularity_rank` | INTEGER |  |
| `num_list_users` | BIGINT |  |
| `num_scoring_users` | BIGINT |  |
| `nsfw_level` | VARCHAR |  |
| `extracted_at` | TIMESTAMP |  |
| `_genres` | STRUCT(id INTEGER, "name" VARCHAR)[] |  |
| `_authors` | STRUCT(node STRUCT(id INTEGER, first_name VARCHAR, last_name VARCHAR), "role" VARCHAR)[] |  |
| `_serialization` | STRUCT(node STRUCT(id INTEGER, "name" VARCHAR))[] |  |
| `_related_anime` | STRUCT(node STRUCT(id INTEGER), relation_type VARCHAR)[] |  |

### `staging.stg_mal__manga_anime_links` · view

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `mal_id` | INTEGER |  |
| `relation_type` | VARCHAR |  |

### `staging.stg_mal__manga_authors` · view

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `author_id` | INTEGER |  |
| `author_name` | VARCHAR |  |
| `author_role` | VARCHAR |  |

### `staging.stg_mal__manga_genres` · view

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `genre_id` | INTEGER |  |
| `genre_name` | VARCHAR |  |

### `staging.stg_mal__manga_serialization` · view

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `magazine_id` | INTEGER |  |
| `magazine_name` | VARCHAR |  |

### `staging.stg_mal__user_animelist` · view

Lista pública do usuário configurado (MAL_USERNAME), extração mais recente.

Testes: `accepted_values(list_status)`, `unique_combination`, `value_between(user_score)`

| coluna | tipo | descrição |
|---|---|---|
| `username` | VARCHAR |  |
| `mal_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `list_status` | VARCHAR |  |
| `user_score` | INTEGER |  |
| `episodes_watched` | INTEGER |  |
| `is_rewatching` | BOOLEAN |  |
| `times_rewatched` | INTEGER |  |
| `started_on` | DATE |  |
| `finished_on` | DATE |  |
| `list_updated_at` | TIMESTAMP WITH TIME ZONE |  |
| `extracted_at` | TIMESTAMP |  |

### `staging.stg_manami__anime` · view

anime-offline-database, snapshot mais recente, restrito a entradas com ID do MAL. Traz IDs cruzados (AniList, Kitsu, AniDB), tags temáticas e a nota agregada entre sites.

Testes: `not_null(mal_id)`, `unique(mal_id)`, `value_between(cross_site_score_median)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `anilist_id` | INTEGER |  |
| `kitsu_id` | INTEGER |  |
| `anidb_id` | INTEGER |  |
| `num_sources` | BIGINT |  |
| `title` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `num_episodes` | INTEGER |  |
| `airing_status` | VARCHAR |  |
| `season_name` | VARCHAR |  |
| `season_year` | INTEGER |  |
| `cross_site_score_median` | DOUBLE | Mediana da nota nos vários sites, normalizada para 1–10 pelo manami. |
| `cross_site_score_mean` | DOUBLE |  |
| `tags` | VARCHAR[] |  |
| `studios` | VARCHAR[] |  |
| `synonyms` | VARCHAR[] |  |
| `dataset_date` | DATE |  |

### `staging.stg_manami__anime_tags` · view

Tags temáticas (time travel, isekai, found family...), mais granulares que os gêneros do MAL.

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `tag` | VARCHAR |  |

## intermediate

### `intermediate.int_anime__franchises` · table

Componentes conexos do grafo de relações (sequel, prequel, side story...) = franquias.

Testes: `not_null(franchise_id)`, `not_null(mal_id)`, `unique(mal_id)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `franchise_id` | INTEGER | Menor mal_id da franquia (estável e determinístico). |
| `franchise_size` | BIGINT |  |

### `intermediate.int_anime__score_dispersion` · view

Forma da distribuição de notas — desvio-padrão, entropia e índice de polarização.

Testes: `not_null(mal_id)`, `unique(mal_id)`, `value_between(normalized_entropy)`, `value_between(polarization_index)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `total_votes` | HUGEINT |  |
| `dist_mean` | DOUBLE |  |
| `score_stddev` | DOUBLE |  |
| `share_10` | DOUBLE |  |
| `share_9_10` | DOUBLE |  |
| `share_5_8` | DOUBLE |  |
| `share_1_4` | DOUBLE |  |
| `normalized_entropy` | DOUBLE |  |
| `mode_score` | INTEGER |  |
| `polarization_index` | DOUBLE |  |

### `intermediate.int_anime__weighted_score` · view

Nota bayesiana (estilo IMDb) que penaliza títulos com poucos votos.

Testes: `assert_weighted_score_within_bounds`, `not_null(mal_id)`, `unique(mal_id)`, `value_between(weighted_score)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `mean_score` | DOUBLE |  |
| `num_scoring_users` | BIGINT |  |
| `global_mean` | DOUBLE |  |
| `prior_votes` | DOUBLE |  |
| `weighted_score` | DOUBLE |  |

### `intermediate.int_manga__anime_links` · view

Ligações mangá × anime unindo MAL (related_anime do mangá) e AniList (obra de origem do anime), no vocabulário de relações do MAL. Uma linha por (mangá, anime, tipo de relação).

Testes: `accepted_values(link_sources)`, `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `mal_id` | INTEGER |  |
| `relation_type` | VARCHAR |  |
| `link_sources` | VARCHAR |  |

### `intermediate.int_users__ratings_normalized` · view

Notas da base Kaggle normalizadas por usuário (centralizadas e z-score).

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `user_key` | VARCHAR |  |
| `mal_id` | INTEGER |  |
| `user_score` | INTEGER |  |
| `list_status` | VARCHAR |  |
| `n_ratings` | BIGINT |  |
| `user_mean` | DOUBLE |  |
| `user_stddev` | DOUBLE |  |
| `score_centered` | DOUBLE |  |
| `score_z` | DOUBLE |  |

## core

### `core.bridge_anime_cast` · table

Anime × personagem × dublador (AniList). person_id nulo = personagem sem dublador cadastrado.

Testes: `accepted_values(character_role)`, `relationships(character_id)`, `relationships(mal_id)`, `relationships(person_id)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `character_id` | INTEGER |  |
| `character_role` | VARCHAR |  |
| `person_id` | INTEGER |  |
| `voice_language` | VARCHAR |  |

### `core.bridge_anime_genre` · table

Anime × gênero (N:N). allocation_weight divide 1 entre os gêneros do anime para somas sem dupla contagem.

Testes: `relationships(genre_id)`, `relationships(mal_id)`, `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `genre_id` | INTEGER |  |
| `allocation_weight` | DOUBLE |  |

### `core.bridge_anime_staff` · table

Créditos de staff (AniList) — anime × pessoa × papel, com `role_group` normalizado.

Testes: `accepted_values(role_group)`, `relationships(person_id)`, `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `person_id` | INTEGER |  |
| `role` | VARCHAR |  |
| `role_base` | VARCHAR |  |
| `role_group` | VARCHAR |  |

### `core.bridge_anime_studio` · table

Anime × estúdio (N:N).

Testes: `relationships(studio_id)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `studio_id` | INTEGER |  |
| `is_main_studio` | BOOLEAN |  |

### `core.bridge_manga_anime` · table

Mangá × anime (adaptações e outras ligações, MAL + AniList). `link_sources` diz quem confirmou.

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `mal_id` | INTEGER |  |
| `relation_type` | VARCHAR |  |
| `link_sources` | VARCHAR |  |

### `core.bridge_manga_author` · table

Mangá × autor (com o papel — história, arte...).

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `author_id` | INTEGER |  |
| `author_name` | VARCHAR |  |
| `author_role` | VARCHAR |  |

### `core.dim_anime` · table

Dimensão central do projeto — **uma linha por anime do MAL**.

Junta o estado mais recente da MAL API com: estúdio principal, gêneros, franquia
(componente conexo do grafo de relações), nota bayesiana, métricas de polarização
(Jikan), taxas de conclusão/abandono e IDs de AniList/Kitsu/AniDB (manami).

Testes: `accepted_values(score_band)`, `not_null(franchise_id)`, `not_null(mal_id)`, `not_null(title)`, `relationships(mal_id)`, `row_count_at_least`, `unique(mal_id)`, `value_between(completion_rate)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `title_english` | VARCHAR |  |
| `title_japanese` | VARCHAR |  |
| `mal_url` | VARCHAR |  |
| `picture_url` | VARCHAR |  |
| `synopsis` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `airing_status` | VARCHAR |  |
| `num_episodes` | INTEGER |  |
| `episode_duration_min` | DOUBLE |  |
| `total_runtime_hours` | DOUBLE |  |
| `source_material` | VARCHAR |  |
| `age_rating` | VARCHAR |  |
| `main_studio_id` | INTEGER |  |
| `main_studio_name` | VARCHAR |  |
| `genres` | VARCHAR[] |  |
| `genres_label` | VARCHAR |  |
| `tags` | VARCHAR[] |  |
| `start_date` | DATE |  |
| `end_date` | DATE |  |
| `start_date_precision` | VARCHAR |  |
| `season_year` | BIGINT |  |
| `season_name` | VARCHAR |  |
| `season_key` | VARCHAR | Chave ordenável de temporada no formato 2024-Q4-fall. |
| `decade` | BIGINT |  |
| `franchise_id` | INTEGER | Menor mal_id da franquia; animes avulsos são a própria franquia. |
| `franchise_size` | BIGINT |  |
| `is_sequel` | BOOLEAN |  |
| `has_sequel` | BOOLEAN |  |
| `mean_score` | DOUBLE |  |
| `weighted_score` | DOUBLE | Nota bayesiana (ver int_anime__weighted_score). |
| `score_rank` | INTEGER |  |
| `popularity_rank` | INTEGER |  |
| `num_list_users` | BIGINT |  |
| `num_scoring_users` | BIGINT |  |
| `score_band` | VARCHAR |  |
| `completion_rate` | DOUBLE | completed / (completed + dropped). Proxy de "quantos terminam o que começam". |
| `drop_rate` | DOUBLE |  |
| `plan_to_watch_share` | DOUBLE |  |
| `score_stddev` | DOUBLE |  |
| `polarization_index` | DOUBLE | 4 × share(9–10) × share(1–4). 0 = consenso, 1 = metade ama / metade odeia. |
| `normalized_entropy` | DOUBLE |  |
| `share_10` | DOUBLE |  |
| `anilist_id` | INTEGER |  |
| `kitsu_id` | INTEGER |  |
| `anidb_id` | INTEGER |  |
| `cross_site_score_median` | DOUBLE |  |
| `last_extracted_at` | TIMESTAMP |  |

### `core.dim_character` · table

Personagens (AniList), com favoritos e número de animes em que aparecem.

Testes: `not_null(character_id)`, `relationships(character_id)`, `unique(character_id)`

| coluna | tipo | descrição |
|---|---|---|
| `character_id` | INTEGER |  |
| `character_name` | VARCHAR |  |
| `character_name_native` | VARCHAR |  |
| `gender` | VARCHAR |  |
| `age` | VARCHAR |  |
| `favourites` | INTEGER |  |
| `num_anime_appearances` | BIGINT |  |
| `ever_main` | BOOLEAN |  |
| `image_url` | VARCHAR |  |
| `profile_url` | VARCHAR |  |

### `core.dim_genre` · table

Gêneros/temas/demografias do MAL e quantos animes há em cada.

Testes: `relationships(genre_id)`, `unique(genre_id)`

| coluna | tipo | descrição |
|---|---|---|
| `genre_id` | INTEGER |  |
| `genre_name` | VARCHAR |  |
| `num_anime` | BIGINT |  |

### `core.dim_manga` · table

Mangás, light novels, manhwas etc. do MAL, com autores, revista e se viraram anime.

Testes: `not_null(manga_id)`, `unique(manga_id)`, `value_between(mean_score)`

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `title_english` | VARCHAR |  |
| `mal_url` | VARCHAR |  |
| `picture_url` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `publishing_status` | VARCHAR |  |
| `start_date` | DATE |  |
| `end_date` | DATE |  |
| `start_year` | BIGINT |  |
| `num_volumes` | INTEGER |  |
| `num_chapters` | INTEGER |  |
| `mean_score` | DOUBLE |  |
| `score_rank` | INTEGER |  |
| `popularity_rank` | INTEGER |  |
| `num_list_users` | BIGINT |  |
| `num_scoring_users` | BIGINT |  |
| `genres` | VARCHAR[] |  |
| `genres_label` | VARCHAR |  |
| `authors_label` | VARCHAR |  |
| `magazines_label` | VARCHAR |  |
| `has_anime_adaptation` | BOOLEAN |  |
| `num_anime_adaptations` | BIGINT |  |
| `main_adaptation_title` | VARCHAR |  |
| `main_adaptation_score` | DOUBLE |  |
| `years_until_adaptation` | BIGINT |  |

### `core.dim_person` · table

Pessoas do ecossistema (dubladores e staff) com ficha da AniList e tamanho da carreira nos dados.

Testes: `not_null(person_id)`, `relationships(person_id)`, `unique(person_id)`

| coluna | tipo | descrição |
|---|---|---|
| `person_id` | INTEGER |  |
| `person_name` | VARCHAR |  |
| `person_name_native` | VARCHAR |  |
| `language` | VARCHAR |  |
| `gender` | VARCHAR |  |
| `birth_date` | DATE |  |
| `death_date` | DATE |  |
| `home_town` | VARCHAR |  |
| `active_since` | INTEGER |  |
| `occupations` | VARCHAR[] |  |
| `favourites` | INTEGER |  |
| `num_anime_voiced` | BIGINT |  |
| `num_characters` | BIGINT |  |
| `num_main_roles` | BIGINT |  |
| `num_anime_staff` | BIGINT |  |
| `num_anime_directed` | BIGINT |  |
| `main_role_group` | VARCHAR |  |
| `image_url` | VARCHAR |  |
| `profile_url` | VARCHAR |  |

### `core.dim_studio` · table

Estúdios de animação com volume e período de atividade.

Testes: `relationships(studio_id)`, `unique(studio_id)`

| coluna | tipo | descrição |
|---|---|---|
| `studio_id` | INTEGER |  |
| `studio_name` | VARCHAR |  |
| `num_anime` | BIGINT |  |
| `num_anime_as_main` | BIGINT |  |
| `first_year` | INTEGER |  |
| `last_year` | INTEGER |  |

### `core.fct_anime_metrics_snapshot` · incremental

Série temporal (incremental) de métricas por anime e dia de extração — nota, rank, membros e contagem por status. Cresce a cada execução semanal do pipeline.

Testes: `unique_combination`, `value_between(num_list_users)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `snapshot_date` | DATE |  |
| `mean_score` | DOUBLE |  |
| `score_rank` | INTEGER |  |
| `popularity_rank` | INTEGER |  |
| `num_list_users` | BIGINT |  |
| `num_scoring_users` | BIGINT |  |
| `status_watching` | BIGINT |  |
| `status_completed` | BIGINT |  |
| `status_on_hold` | BIGINT |  |
| `status_dropped` | BIGINT |  |
| `status_plan_to_watch` | BIGINT |  |
| `extracted_at` | TIMESTAMP |  |

### `core.fct_episode` · table

Episódios (Kitsu) ligados ao anime do MAL — título, temporada, data de exibição e duração.

Testes: `not_null(episode_number)`, `unique_combination`, `value_between(length_min)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `episode_number` | INTEGER |  |
| `season_number` | INTEGER |  |
| `episode_title` | VARCHAR |  |
| `aired_on` | DATE |  |
| `aired_year` | BIGINT |  |
| `length_min` | INTEGER |  |
| `days_since_previous` | BIGINT |  |
| `synopsis` | VARCHAR |  |

### `core.fct_my_list` · table

A sua lista do MAL enriquecida com a nota da comunidade e metadados.

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `username` | VARCHAR |  |
| `mal_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `list_status` | VARCHAR |  |
| `user_score` | INTEGER |  |
| `mal_mean_score` | DOUBLE |  |
| `score_delta` | DOUBLE | Sua nota menos a média do MAL. Positivo = você gostou mais que a média. |
| `episodes_watched` | INTEGER |  |
| `hours_watched` | DOUBLE |  |
| `is_rewatching` | BOOLEAN |  |
| `times_rewatched` | INTEGER |  |
| `started_on` | DATE |  |
| `finished_on` | DATE |  |
| `finished_year` | BIGINT |  |
| `media_type` | VARCHAR |  |
| `season_year` | BIGINT |  |
| `main_studio_name` | VARCHAR |  |
| `genres` | VARCHAR[] |  |
| `mal_members` | BIGINT |  |
| `list_updated_at` | TIMESTAMP WITH TIME ZONE |  |

### `core.fct_user_rating` · table

Interações usuário × anime (Kaggle 2020). Grão user_key × mal_id.

Testes: `not_null(user_key)`, `relationships(mal_id)`

| coluna | tipo | descrição |
|---|---|---|
| `user_key` | VARCHAR |  |
| `mal_id` | INTEGER | Pode haver IDs que não existem mais no MAL atual (dataset de 2020) — por isso o teste de integridade é só um aviso.  |
| `list_status` | VARCHAR |  |
| `user_score` | INTEGER |  |
| `episodes_watched` | INTEGER |  |
| `score_centered` | DOUBLE |  |
| `score_z` | DOUBLE |  |
| `is_dropped` | BOOLEAN |  |
| `is_completed` | BOOLEAN |  |

## analytics

### `analytics.mart_adaptation_scores` · table

Nota da obra original × nota de cada adaptação em anime.

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `manga_title` | VARCHAR |  |
| `source_type` | VARCHAR |  |
| `manga_score` | DOUBLE |  |
| `mal_id` | INTEGER |  |
| `anime_title` | VARCHAR |  |
| `anime_media_type` | VARCHAR |  |
| `anime_score` | DOUBLE |  |
| `anime_minus_manga` | DOUBLE |  |
| `main_studio_name` | VARCHAR |  |
| `season_year` | BIGINT |  |
| `years_after_original` | BIGINT |  |

### `analytics.mart_anime_trending` · table

Variação de nota, membros e rank entre as duas extrações mais recentes de cada anime.

Testes: `not_null(mal_id)`, `unique(mal_id)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `airing_status` | VARCHAR |  |
| `snapshot_date` | DATE |  |
| `prev_snapshot_date` | DATE |  |
| `days_between` | BIGINT |  |
| `mean_score` | DOUBLE |  |
| `score_change` | DOUBLE |  |
| `members` | BIGINT |  |
| `members_gained` | BIGINT |  |
| `members_growth_rate` | DOUBLE |  |
| `rank_positions_gained` | INTEGER |  |

### `analytics.mart_director_performance` · table

Diretores (3+ obras com nota) — mediana, consistência, alcance e melhor obra.

Testes: `not_null(person_id)`, `unique(person_id)`

| coluna | tipo | descrição |
|---|---|---|
| `person_id` | INTEGER |  |
| `person_name` | VARCHAR |  |
| `person_name_native` | VARCHAR |  |
| `num_titles` | BIGINT |  |
| `median_score` | DOUBLE |  |
| `avg_score` | DOUBLE |  |
| `score_stddev` | DOUBLE |  |
| `members_weighted_score` | DOUBLE |  |
| `total_members` | HUGEINT |  |
| `best_title` | VARCHAR |  |
| `best_score` | DOUBLE |  |
| `usual_studio` | VARCHAR |  |
| `first_year` | BIGINT |  |
| `last_year` | BIGINT |  |
| `person_favourites` | INTEGER |  |

### `analytics.mart_drop_rate_by_genre` · table

Taxa de abandono por gênero a partir do comportamento real dos usuários (Kaggle).

Testes: `not_null(genre_id)`, `unique(genre_id)`, `value_between(drop_rate)`

| coluna | tipo | descrição |
|---|---|---|
| `genre_id` | INTEGER |  |
| `genre_name` | VARCHAR |  |
| `num_interactions` | BIGINT |  |
| `num_dropped` | BIGINT |  |
| `drop_rate` | DOUBLE |  |
| `avg_score_when_completed` | DOUBLE |  |
| `avg_score_when_dropped` | DOUBLE |  |

### `analytics.mart_episode_trends` · table

Episódios exibidos por ano — volume, animes no ar e duração média.

Testes: `not_null(aired_year)`, `unique(aired_year)`

| coluna | tipo | descrição |
|---|---|---|
| `aired_year` | BIGINT |  |
| `episodes_aired` | BIGINT |  |
| `anime_airing` | BIGINT |  |
| `avg_length_min` | DOUBLE |  |
| `total_hours` | DOUBLE |  |
| `share_web_episodes` | DOUBLE |  |

### `analytics.mart_franchise_summary` · table

Resumo por franquia (2+ entradas). Nome = entrada mais popular; evolução da nota compara a primeira e a última temporada de TV (nula se a franquia tem menos de 2 entradas de TV com nota).

Testes: `not_null(franchise_id)`, `unique(franchise_id)`, `value_between(num_entries)`

| coluna | tipo | descrição |
|---|---|---|
| `franchise_id` | INTEGER |  |
| `franchise_name` | VARCHAR |  |
| `num_entries` | BIGINT |  |
| `num_tv_entries` | BIGINT |  |
| `total_episodes` | HUGEINT |  |
| `total_runtime_hours` | DOUBLE |  |
| `first_year` | BIGINT |  |
| `last_year` | BIGINT |  |
| `avg_score` | DOUBLE |  |
| `best_score` | DOUBLE |  |
| `best_entry` | VARCHAR |  |
| `first_tv_entry` | VARCHAR |  |
| `first_entry_score` | DOUBLE |  |
| `latest_tv_entry` | VARCHAR |  |
| `latest_entry_score` | DOUBLE |  |
| `score_change_first_to_latest` | DOUBLE |  |
| `peak_members` | BIGINT |  |
| `total_members` | HUGEINT |  |

### `analytics.mart_genre_trends` · table

Gênero × ano — participação no catálogo, nota média e audiência.

Testes: `unique_combination`, `value_between(share_of_year)`

| coluna | tipo | descrição |
|---|---|---|
| `season_year` | BIGINT |  |
| `genre_id` | INTEGER |  |
| `genre_name` | VARCHAR |  |
| `num_titles` | BIGINT |  |
| `share_of_year` | DOUBLE |  |
| `avg_score` | DOUBLE |  |
| `total_members` | HUGEINT |  |
| `allocated_members` | BIGINT |  |

### `analytics.mart_hidden_gems` · table

Nota no topo (entre títulos com votos suficientes) e poucos membros — boas descobertas.

Testes: `not_null(mal_id)`, `unique(mal_id)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `season_year` | BIGINT |  |
| `main_studio_name` | VARCHAR |  |
| `genres_label` | VARCHAR |  |
| `mean_score` | DOUBLE |  |
| `weighted_score` | DOUBLE |  |
| `num_scoring_users` | BIGINT |  |
| `num_list_users` | BIGINT |  |
| `members_percentile` | DOUBLE |  |
| `quality_percentile` | DOUBLE |  |
| `gem_score` | DOUBLE |  |
| `mal_url` | VARCHAR |  |

### `analytics.mart_manga_adaptation_gap` · table

Obras originais populares e bem avaliadas que ainda não viraram anime.

Testes: `not_null(manga_id)`, `unique(manga_id)`

| coluna | tipo | descrição |
|---|---|---|
| `manga_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `publishing_status` | VARCHAR |  |
| `start_year` | BIGINT |  |
| `authors_label` | VARCHAR |  |
| `magazines_label` | VARCHAR |  |
| `genres_label` | VARCHAR |  |
| `mean_score` | DOUBLE |  |
| `num_list_users` | BIGINT |  |
| `num_scoring_users` | BIGINT |  |
| `num_volumes` | INTEGER |  |
| `num_chapters` | INTEGER |  |
| `popularity_rank_unadapted` | BIGINT |  |
| `mal_url` | VARCHAR |  |

### `analytics.mart_my_profile_vs_mal` · table

Sua nota vs a da comunidade por gênero, estúdio, formato e década (formato longo).

Testes: `accepted_values(dimension)`, `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `username` | VARCHAR |  |
| `dimension` | VARCHAR |  |
| `value` | VARCHAR |  |
| `num_titles` | BIGINT |  |
| `my_avg_score` | DOUBLE |  |
| `mal_avg_score` | DOUBLE |  |
| `delta_avg` | DOUBLE |  |
| `correlation_with_mal` | DOUBLE |  |

### `analytics.mart_polarizing_anime` · table

Animes mais polarizadores ("ame ou odeie"), com volume mínimo de votos.

Testes: `not_null(mal_id)`, `unique(mal_id)`

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `title` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `season_year` | BIGINT |  |
| `main_studio_name` | VARCHAR |  |
| `genres_label` | VARCHAR |  |
| `mean_score` | DOUBLE |  |
| `total_votes` | HUGEINT |  |
| `score_stddev` | DOUBLE |  |
| `polarization_index` | DOUBLE |  |
| `normalized_entropy` | DOUBLE |  |
| `share_9_10` | DOUBLE |  |
| `share_1_4` | DOUBLE |  |
| `mode_score` | INTEGER |  |
| `polarization_rank` | BIGINT |  |

### `analytics.mart_score_inflation` · table

Distribuição de notas por ano de estreia, para investigar inflação de notas.

Testes: `not_null(season_year)`, `unique(season_year)`

| coluna | tipo | descrição |
|---|---|---|
| `season_year` | BIGINT |  |
| `num_titles` | BIGINT |  |
| `avg_score` | DOUBLE |  |
| `median_score` | DOUBLE |  |
| `p10_score` | DOUBLE |  |
| `p90_score` | DOUBLE |  |
| `avg_weighted_score` | DOUBLE |  |
| `avg_within_title_stddev` | DOUBLE |  |
| `total_votes` | HUGEINT |  |
| `diff_vs_overall_avg` | DOUBLE |  |

### `analytics.mart_season_trends` · table

Panorama por temporada — volume, nota, destaque, peso de sequências e de cada origem.

Testes: `not_null(season_key)`, `unique(season_key)`

| coluna | tipo | descrição |
|---|---|---|
| `season_key` | VARCHAR |  |
| `season_year` | BIGINT |  |
| `season_name` | VARCHAR |  |
| `season_number` | INTEGER |  |
| `num_titles` | BIGINT |  |
| `num_scored` | BIGINT |  |
| `avg_score` | DOUBLE |  |
| `median_score` | DOUBLE |  |
| `top_title` | VARCHAR |  |
| `top_score` | DOUBLE |  |
| `most_popular_title` | VARCHAR |  |
| `total_members` | HUGEINT |  |
| `share_sequels` | DOUBLE |  |
| `share_original` | DOUBLE |  |
| `share_manga` | DOUBLE |  |
| `share_light_novel` | DOUBLE |  |

### `analytics.mart_seiyuu_network` · table

Arestas do grafo de dubladores (co-protagonismo), prontas para Gephi/NetworkX.

Testes: `unique_combination`

| coluna | tipo | descrição |
|---|---|---|
| `person_a` | INTEGER |  |
| `person_b` | INTEGER |  |
| `person_a_name` | VARCHAR |  |
| `person_b_name` | VARCHAR |  |
| `shared_anime` | BIGINT |  |
| `shared_titles` | VARCHAR[] |  |

### `analytics.mart_studio_performance` · table

Ranking de estúdios por qualidade (nota bayesiana ponderada), consistência e alcance.

Testes: `not_null(studio_id)`, `unique(studio_id)`, `value_between(num_titles)`

| coluna | tipo | descrição |
|---|---|---|
| `studio_id` | INTEGER |  |
| `studio_name` | VARCHAR |  |
| `num_titles` | BIGINT |  |
| `first_year` | BIGINT |  |
| `last_year` | BIGINT |  |
| `vote_weighted_score` | DOUBLE |  |
| `avg_weighted_score` | DOUBLE |  |
| `median_score` | DOUBLE |  |
| `score_stddev` | DOUBLE |  |
| `share_titles_8_plus` | DOUBLE |  |
| `total_members` | HUGEINT |  |
| `best_title` | VARCHAR |  |
| `best_weighted_score` | DOUBLE |  |
| `worst_title` | VARCHAR |  |
| `share_sequels` | DOUBLE |  |
| `most_common_source` | VARCHAR |  |
| `quality_rank` | BIGINT |  |
| `consistency_rank` | BIGINT |  |
| `reach_rank` | BIGINT |  |

### `analytics.mart_voice_actor_ranking` · table

Dubladores por volume, protagonismo, nota média dos animes e papel mais famoso.

Testes: `not_null(person_id)`, `unique(person_id)`

| coluna | tipo | descrição |
|---|---|---|
| `person_id` | INTEGER |  |
| `person_name` | VARCHAR |  |
| `person_name_native` | VARCHAR |  |
| `voice_language` | VARCHAR |  |
| `gender` | VARCHAR |  |
| `birth_date` | DATE |  |
| `person_favourites` | INTEGER |  |
| `num_anime` | BIGINT |  |
| `num_characters` | BIGINT |  |
| `num_main_roles` | BIGINT |  |
| `avg_anime_score` | DOUBLE |  |
| `total_members_reached` | HUGEINT |  |
| `most_famous_character` | VARCHAR |  |
| `most_famous_character_anime` | VARCHAR |  |
| `first_year` | BIGINT |  |
| `last_year` | BIGINT |  |
| `rank_by_volume` | BIGINT |  |

## snapshots

### `snapshots.snap_anime_status` · snapshot

SCD tipo 2 de atributos que mudam raramente (status de exibição, episódios, título). Responde perguntas como "quando este anime passou de not_yet_aired para currently_airing?" ou "quantas vezes o número de episódios anunciado mudou?".

| coluna | tipo | descrição |
|---|---|---|
| `mal_id` | INTEGER |  |
| `extracted_at` | TIMESTAMP |  |
| `snapshot_date` | DATE |  |
| `title` | VARCHAR |  |
| `title_english` | VARCHAR |  |
| `title_japanese` | VARCHAR |  |
| `synopsis` | VARCHAR |  |
| `background` | VARCHAR |  |
| `picture_url_large` | VARCHAR |  |
| `picture_url` | VARCHAR |  |
| `media_type` | VARCHAR |  |
| `airing_status` | VARCHAR |  |
| `num_episodes` | INTEGER |  |
| `episode_duration_sec` | INTEGER |  |
| `source_material` | VARCHAR |  |
| `age_rating` | VARCHAR |  |
| `nsfw_level` | VARCHAR |  |
| `start_date_raw` | VARCHAR |  |
| `start_date` | DATE |  |
| `start_date_precision` | VARCHAR |  |
| `end_date` | DATE |  |
| `season_year` | INTEGER |  |
| `season_name` | VARCHAR |  |
| `broadcast_day` | VARCHAR |  |
| `broadcast_time_jst` | VARCHAR |  |
| `mean_score` | DOUBLE |  |
| `score_rank` | INTEGER |  |
| `popularity_rank` | INTEGER |  |
| `num_list_users` | BIGINT |  |
| `num_scoring_users` | BIGINT |  |
| `status_watching` | BIGINT |  |
| `status_completed` | BIGINT |  |
| `status_on_hold` | BIGINT |  |
| `status_dropped` | BIGINT |  |
| `status_plan_to_watch` | BIGINT |  |
| `mal_created_at` | TIMESTAMP WITH TIME ZONE |  |
| `mal_updated_at` | TIMESTAMP WITH TIME ZONE |  |
| `dbt_scd_id` | VARCHAR |  |
| `dbt_updated_at` | TIMESTAMP |  |
| `dbt_valid_from` | TIMESTAMP |  |
| `dbt_valid_to` | TIMESTAMP |  |
