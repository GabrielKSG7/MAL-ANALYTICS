{#
  A média do MAL esconde o formato da distribuição: dois animes com 7.5 podem ser um
  "consenso morno" ou um "ame ou odeie". Aqui calculamos métricas de forma da distribuição.

  polarization_index = 4 × share(9–10) × share(1–4)
    → 0 quando um dos extremos está vazio; 1 quando metade dá 9–10 e metade dá 1–4.
  normalized_entropy = entropia de Shannon / ln(10)
    → 0 = todos deram a mesma nota; 1 = votos espalhados uniformemente.
#}
with dist as (
    select mal_id, score, votes
    from {{ ref('stg_jikan__score_distribution') }}
),

totals as (
    select
        mal_id,
        sum(votes)                                        as total_votes,
        sum(score * votes) / nullif(sum(votes), 0)        as dist_mean
    from dist
    group by mal_id
),

shaped as (
    select
        d.mal_id,
        t.total_votes,
        t.dist_mean,
        sqrt(sum(d.votes * power(d.score - t.dist_mean, 2)) / nullif(t.total_votes, 0)) as score_stddev,
        sum(d.votes) filter (where d.score = 10)              / nullif(t.total_votes, 0) as share_10,
        sum(d.votes) filter (where d.score >= 9)              / nullif(t.total_votes, 0) as share_9_10,
        sum(d.votes) filter (where d.score between 5 and 8)   / nullif(t.total_votes, 0) as share_5_8,
        sum(d.votes) filter (where d.score <= 4)              / nullif(t.total_votes, 0) as share_1_4,
        -sum(case when d.votes > 0
                  then (d.votes / t.total_votes) * ln(d.votes / t.total_votes) end) / ln(10)
                                                                                        as normalized_entropy,
        arg_max(d.score, d.votes)                                                       as mode_score
    from dist d
    join totals t using (mal_id)
    where t.total_votes > 0
    group by d.mal_id, t.total_votes, t.dist_mean
)

select
    *,
    4 * coalesce(share_9_10, 0) * coalesce(share_1_4, 0) as polarization_index
from shaped
