# Lineage

> Gerado por `scripts/gen_lineage.py` a partir do manifest do dbt — não edite à mão.
> Para o lineage interativo, modelo a modelo: `make dbt-docs`.

## Visão geral

```mermaid
flowchart LR
  src_anilist[("AniList GraphQL")] --> stg["Staging · 26 modelos"]
  src_jikan[("Jikan")] --> stg["Staging · 26 modelos"]
  src_kaggle[("Kaggle (interações)")] --> stg["Staging · 26 modelos"]
  src_kitsu[("Kitsu")] --> stg["Staging · 26 modelos"]
  src_mal[("MyAnimeList API")] --> stg["Staging · 26 modelos"]
  src_manami[("anime-offline-database")] --> stg["Staging · 26 modelos"]
  stg --> int["Intermediate · 5"]
  int --> core["Core · 16"]
  stg --> core
  core --> an["Analytics · 16"]
  core --> rec{{"Recomendador (Python)"}}
  an --> dash{{"Dashboard Streamlit"}}
  an --> site{{"Painel público (GitHub Pages)"}}
  an --> dbeaver{{"Cópia de consulta (DBeaver)"}}
```

## Modelo a modelo

Staging agrupado por fonte; da camada intermediate em diante, cada nó é um modelo.

```mermaid
flowchart LR
  subgraph Fontes["Fontes (bronze)"]
    src_anilist[("AniList GraphQL")]
    src_jikan[("Jikan")]
    src_kaggle[("Kaggle (interações)")]
    src_kitsu[("Kitsu")]
    src_mal[("MyAnimeList API")]
    src_manami[("anime-offline-database")]
  end
  subgraph Staging["Staging · views tipadas"]
    stg_anilist["anilist · 8 modelos"]
    stg_jikan["jikan · 3 modelos"]
    stg_kaggle["kaggle · 1 modelos"]
    stg_kitsu["kitsu · 1 modelos"]
    stg_mal["mal · 11 modelos"]
    stg_manami["manami · 2 modelos"]
  end
  subgraph Intermediate["Intermediate"]
    int_anime__franchises
    int_anime__score_dispersion
    int_anime__weighted_score
    int_manga__anime_links
    int_users__ratings_normalized
  end
  subgraph Core["Core · dimensões e fatos"]
    bridge_anime_cast
    bridge_anime_genre
    bridge_anime_staff
    bridge_anime_studio
    bridge_manga_anime
    bridge_manga_author
    dim_anime
    dim_character
    dim_genre
    dim_manga
    dim_person
    dim_studio
    fct_anime_metrics_snapshot
    fct_episode
    fct_my_list
    fct_user_rating
  end
  subgraph Analytics["Analytics · marts por pergunta"]
    mart_adaptation_scores
    mart_anime_trending
    mart_director_performance
    mart_drop_rate_by_genre
    mart_episode_trends
    mart_franchise_summary
    mart_genre_trends
    mart_hidden_gems
    mart_manga_adaptation_gap
    mart_my_profile_vs_mal
    mart_polarizing_anime
    mart_score_inflation
    mart_season_trends
    mart_seiyuu_network
    mart_studio_performance
    mart_voice_actor_ranking
  end
  subgraph Entregas["Exposures"]
    exp_public_site{{"Painel público (GitHub Pages)"}}
    exp_recommender{{"Recomendador (malpipe.recsys)"}}
    exp_streamlit_dashboard{{"Dashboard MAL Analytics (Streamlit)"}}
  end
  bridge_anime_cast --> mart_seiyuu_network
  bridge_anime_cast --> mart_voice_actor_ranking
  bridge_anime_genre --> mart_drop_rate_by_genre
  bridge_anime_genre --> mart_genre_trends
  bridge_anime_staff --> mart_director_performance
  bridge_manga_anime --> mart_adaptation_scores
  dim_anime --> bridge_manga_anime
  dim_anime --> dim_manga
  dim_anime --> exp_recommender
  dim_anime --> exp_streamlit_dashboard
  dim_anime --> fct_episode
  dim_anime --> fct_my_list
  dim_anime --> mart_adaptation_scores
  dim_anime --> mart_anime_trending
  dim_anime --> mart_director_performance
  dim_anime --> mart_episode_trends
  dim_anime --> mart_franchise_summary
  dim_anime --> mart_genre_trends
  dim_anime --> mart_hidden_gems
  dim_anime --> mart_polarizing_anime
  dim_anime --> mart_score_inflation
  dim_anime --> mart_season_trends
  dim_anime --> mart_seiyuu_network
  dim_anime --> mart_studio_performance
  dim_anime --> mart_voice_actor_ranking
  dim_character --> mart_voice_actor_ranking
  dim_genre --> mart_drop_rate_by_genre
  dim_genre --> mart_genre_trends
  dim_manga --> exp_public_site
  dim_manga --> mart_adaptation_scores
  dim_manga --> mart_manga_adaptation_gap
  dim_person --> mart_director_performance
  dim_person --> mart_seiyuu_network
  dim_person --> mart_voice_actor_ranking
  fct_anime_metrics_snapshot --> mart_anime_trending
  fct_episode --> mart_episode_trends
  fct_my_list --> exp_public_site
  fct_my_list --> exp_recommender
  fct_my_list --> exp_streamlit_dashboard
  fct_my_list --> mart_my_profile_vs_mal
  fct_user_rating --> exp_recommender
  fct_user_rating --> mart_drop_rate_by_genre
  int_anime__franchises --> dim_anime
  int_anime__score_dispersion --> dim_anime
  int_anime__score_dispersion --> mart_polarizing_anime
  int_anime__weighted_score --> dim_anime
  int_manga__anime_links --> bridge_manga_anime
  int_manga__anime_links --> dim_manga
  int_manga__anime_links --> mart_manga_adaptation_gap
  int_users__ratings_normalized --> fct_user_rating
  mart_adaptation_scores --> exp_public_site
  mart_anime_trending --> exp_streamlit_dashboard
  mart_drop_rate_by_genre --> exp_streamlit_dashboard
  mart_episode_trends --> exp_public_site
  mart_franchise_summary --> exp_streamlit_dashboard
  mart_genre_trends --> exp_streamlit_dashboard
  mart_hidden_gems --> exp_streamlit_dashboard
  mart_manga_adaptation_gap --> exp_public_site
  mart_my_profile_vs_mal --> exp_streamlit_dashboard
  mart_polarizing_anime --> exp_streamlit_dashboard
  mart_score_inflation --> exp_public_site
  mart_score_inflation --> exp_streamlit_dashboard
  mart_season_trends --> exp_public_site
  mart_season_trends --> exp_streamlit_dashboard
  mart_studio_performance --> exp_public_site
  mart_studio_performance --> exp_streamlit_dashboard
  mart_voice_actor_ranking --> exp_public_site
  src_anilist --> stg_anilist
  src_jikan --> stg_jikan
  src_kaggle --> stg_kaggle
  src_kitsu --> stg_kitsu
  src_mal --> stg_mal
  src_manami --> stg_manami
  stg_anilist --> bridge_anime_cast
  stg_anilist --> bridge_anime_staff
  stg_anilist --> dim_character
  stg_anilist --> dim_person
  stg_anilist --> int_manga__anime_links
  stg_jikan --> exp_recommender
  stg_jikan --> int_anime__score_dispersion
  stg_kaggle --> fct_user_rating
  stg_kaggle --> int_users__ratings_normalized
  stg_kitsu --> fct_episode
  stg_mal --> bridge_anime_genre
  stg_mal --> bridge_anime_studio
  stg_mal --> bridge_manga_author
  stg_mal --> dim_anime
  stg_mal --> dim_genre
  stg_mal --> dim_manga
  stg_mal --> dim_studio
  stg_mal --> fct_anime_metrics_snapshot
  stg_mal --> fct_my_list
  stg_mal --> int_anime__franchises
  stg_mal --> int_anime__weighted_score
  stg_mal --> int_manga__anime_links
  stg_manami --> dim_anime
```
