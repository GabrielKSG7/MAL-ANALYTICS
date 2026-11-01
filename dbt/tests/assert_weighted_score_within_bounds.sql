-- Propriedade matemática da média bayesiana: ela fica sempre entre a nota do anime e a média global.
select mal_id, mean_score, global_mean, weighted_score
from {{ ref('int_anime__weighted_score') }}
where weighted_score < least(mean_score, global_mean) - 1e-9
   or weighted_score > greatest(mean_score, global_mean) + 1e-9
