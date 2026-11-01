{% docs __overview__ %}
# MAL Analytics

Modelagem analítica sobre o MyAnimeList com quatro fontes:

| Fonte | O que entrega | Camada bronze |
|---|---|---|
| MAL API v2 (oficial) | metadados, nota, rank, membros, status, relações, sua lista | `bronze.mal_anime`, `bronze.mal_user_animelist` |
| Jikan v4 | distribuição de notas 1–10, recomendações da comunidade, elenco | `bronze.jikan_*` |
| anime-offline-database | IDs cruzados entre sites, tags temáticas | `bronze.manami_anime` |
| Kaggle (hernan4444, 2020) | ~109M interações usuário × anime | `bronze.kaggle_animelist` |

**Camadas**: `staging` (views, tipagem e parsing do JSON) → `intermediate` (lógica reutilizável:
franquias por grafo, nota bayesiana, polarização, normalização por usuário) → `core`
(dimensões, pontes e fatos) → `analytics` (marts prontos para perguntas).
{% enddocs %}

{% docs dim_anime %}
Dimensão central do projeto — **uma linha por anime do MAL**.

Junta o estado mais recente da MAL API com: estúdio principal, gêneros, franquia
(componente conexo do grafo de relações), nota bayesiana, métricas de polarização
(Jikan), taxas de conclusão/abandono e IDs de AniList/Kitsu/AniDB (manami).
{% enddocs %}
