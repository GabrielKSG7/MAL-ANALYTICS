{#
  Nota bayesiana (fórmula do Top 250 do IMDb):

      WR = v / (v + m) · R  +  m / (v + m) · C

  R = média do anime, v = nº de votos, C = média global, m = "prior" (percentil de votos).
  Corrige o viés de títulos com poucos votos e nota inflada aparecerem no topo.
#}
with base as (
    select mal_id, mean_score, num_scoring_users
    from {{ ref('stg_mal__anime') }}
    where mean_score is not null and num_scoring_users > 0
),

params as (
    select
        avg(mean_score)                                                         as global_mean,
        quantile_cont(num_scoring_users, {{ var('bayes_prior_percentile') }})   as prior_votes
    from base
)

select
    b.mal_id,
    b.mean_score,
    b.num_scoring_users,
    p.global_mean,
    p.prior_votes,
    (b.num_scoring_users / (b.num_scoring_users + p.prior_votes)) * b.mean_score
      + (p.prior_votes / (b.num_scoring_users + p.prior_votes)) * p.global_mean   as weighted_score
from base b
cross join params p
