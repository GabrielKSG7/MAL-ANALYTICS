"""Dashboard local sobre as marts do dbt e as saídas do recomendador.

    streamlit run dashboard/app.py

Lê o DuckDB em modo somente leitura (DUCKDB_PATH ou data/mal.duckdb).
Paleta: azul como cor única para magnitude; azul ↔ vermelho (com cinza no meio) para
diferenças com sinal, como "minha nota − nota do MAL".
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:  # mesma regra do pipeline: lê DUCKDB_PATH do .env (caminho relativo = raiz do projeto)
    from malpipe.config import get_settings

    DB_PATH = get_settings().duckdb_path
except ImportError:
    DB_PATH = Path(os.getenv("DUCKDB_PATH", Path(__file__).resolve().parents[1] / "data" / "mal.duckdb"))

BLUE = "#2a78d6"
RED = "#e34948"
BLUE_LIGHT = "#9ec5f4"
NEUTRAL = "#8a8985"

st.set_page_config(page_title="MAL Analytics", page_icon="📺", layout="wide")


@st.cache_resource
def connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=600)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    try:
        return connection().execute(sql, list(params)).df()
    except duckdb.Error as exc:  # tabela ausente (ex.: recomendador ainda não rodou)
        st.info(f"Dados indisponíveis: {exc.__class__.__name__}. Rode `make build` (ou `make demo`).")
        return pd.DataFrame()


def style(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=40, b=8),
        hoverlabel=dict(namelength=-1),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridwidth=1)
    return fig


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", theme="streamlit")


if not DB_PATH.exists():
    st.error(f"Banco não encontrado em {DB_PATH}. Rode `make demo` para gerar dados de exemplo.")
    st.stop()

is_sample = not q("SELECT 1 FROM meta.runs WHERE command = 'sample' LIMIT 1").empty
st.title("MAL Analytics")
st.caption(
    "MyAnimeList · Jikan · anime-offline-database · Kaggle — modelado com dbt + DuckDB"
    + (" · ⚠️ **dados sintéticos de demonstração**" if is_sample else "")
)

tabs = st.tabs(
    [
        "Visão geral",
        "Estúdios",
        "Tendências",
        "Polarização & joias",
        "Franquias",
        "Em alta",
        "Abandono",
        "Meu perfil",
        "Recomendações",
    ]  # fmt: skip
)

# ---------------------------------------------------------------- visão geral
with tabs[0]:
    kpi = q(
        """
        SELECT count(*) AS n_anime, count(DISTINCT main_studio_id) AS n_studios,
               round(avg(mean_score), 2) AS avg_score, sum(num_list_users) AS members,
               max(last_extracted_at) AS last_extract
        FROM core.dim_anime
        """
    )
    if not kpi.empty:
        k = kpi.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Animes", f"{int(k.n_anime):,}".replace(",", "."))
        c2.metric("Estúdios", f"{int(k.n_studios):,}".replace(",", "."))
        c3.metric("Nota média", f"{k.avg_score:.2f}")
        c4.metric("Última extração", f"{pd.to_datetime(k.last_extract):%d/%m/%Y}")

    left, right = st.columns(2)
    with left:
        df = q("SELECT mean_score FROM core.dim_anime WHERE mean_score IS NOT NULL")
        if not df.empty:
            fig = px.histogram(df, x="mean_score", nbins=40, title="Distribuição das notas médias",
                               color_discrete_sequence=[BLUE])  # fmt: skip
            fig.update_traces(marker_line_width=2, marker_line_color="rgba(0,0,0,0)")
            show(style(fig).update_layout(bargap=0.08, xaxis_title="nota média", yaxis_title="animes"))
    with right:
        df = q(
            "SELECT score_band, count(*) AS n, min(coalesce(mean_score, 0)) AS lo "
            "FROM core.dim_anime GROUP BY 1 ORDER BY lo"
        )
        if not df.empty:
            fig = px.bar(df, x="n", y="score_band", orientation="h", title="Animes por faixa de nota",
                         color_discrete_sequence=[BLUE], text="n")  # fmt: skip
            show(style(fig).update_layout(xaxis_title="animes", yaxis_title=None))

    st.subheader("Top 25 pela nota bayesiana")
    st.caption("Corrige títulos com poucos votos: WR = v/(v+m)·R + m/(v+m)·C")
    st.dataframe(
        q(
            """
            SELECT title, media_type, season_year, main_studio_name AS studio, genres_label AS genres,
                   mean_score, weighted_score, score_rank, num_list_users AS members
            FROM core.dim_anime WHERE weighted_score IS NOT NULL
            ORDER BY weighted_score DESC LIMIT 25
            """
        ),
        width="stretch",
        hide_index=True,
    )

# ---------------------------------------------------------------- estúdios
with tabs[1]:
    df = q("SELECT * FROM analytics.mart_studio_performance ORDER BY quality_rank")
    if not df.empty:
        left, right = st.columns([3, 2])
        with left:
            top = df.head(15).sort_values("vote_weighted_score")
            fig = px.bar(top, x="vote_weighted_score", y="studio_name", orientation="h",
                         title="Qualidade: nota bayesiana ponderada por votos (top 15)",
                         hover_data=["num_titles", "best_title", "score_stddev"],
                         color_discrete_sequence=[BLUE])  # fmt: skip
            fig.update_xaxes(range=[top.vote_weighted_score.min() - 0.2, top.vote_weighted_score.max() + 0.1])
            show(style(fig, 520).update_layout(xaxis_title="nota", yaxis_title=None))
        with right:
            fig = px.scatter(df, x="score_stddev", y="vote_weighted_score", size="total_members",
                             hover_name="studio_name", hover_data=["num_titles", "best_title"],
                             title="Qualidade × consistência", color_discrete_sequence=[BLUE])  # fmt: skip
            fig.update_traces(marker=dict(line=dict(width=2, color="rgba(255,255,255,0.9)"), sizemin=8))
            show(style(fig, 520).update_layout(xaxis_title="desvio-padrão entre títulos (menor = mais consistente)",
                                               yaxis_title="nota"))  # fmt: skip
        st.dataframe(df, width="stretch", hide_index=True)

# ---------------------------------------------------------------- tendências
with tabs[2]:
    infl = q("SELECT * FROM analytics.mart_score_inflation ORDER BY season_year")
    if not infl.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=infl.season_year, y=infl.p90_score, line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))  # fmt: skip
        fig.add_trace(go.Scatter(x=infl.season_year, y=infl.p10_score, fill="tonexty", line=dict(width=0),
                                 fillcolor="rgba(42,120,214,0.15)", name="faixa p10–p90",
                                 hovertemplate="p10: %{y:.2f}<extra></extra>"))  # fmt: skip
        fig.add_trace(go.Scatter(x=infl.season_year, y=infl.median_score, name="mediana",
                                 line=dict(color=BLUE, width=2), mode="lines+markers", marker=dict(size=8),
                                 hovertemplate="%{x}: mediana %{y:.2f}<extra></extra>"))  # fmt: skip
        fig.update_layout(title="As notas estão inflando? Nota por ano de estreia", hovermode="x unified")
        show(style(fig).update_layout(xaxis_title="ano de estreia", yaxis_title="nota"))
        st.caption("Cuidado com o viés de sobrevivência: títulos antigos ainda votados tendem a ser os clássicos.")

    genres = q("SELECT DISTINCT genre_name FROM analytics.mart_genre_trends ORDER BY 1")
    if not genres.empty:
        pick = st.selectbox("Gênero", genres.genre_name.tolist(), index=0)
        g = q("SELECT * FROM analytics.mart_genre_trends WHERE genre_name = ? ORDER BY season_year", (pick,))
        fig = px.line(g, x="season_year", y="share_of_year", markers=True, color_discrete_sequence=[BLUE],
                      title=f"Participação de {pick} no catálogo do ano",
                      hover_data=["num_titles", "avg_score"])  # fmt: skip
        fig.update_traces(line_width=2, marker_size=8)
        fig.update_yaxes(tickformat=".0%")
        show(style(fig, 360).update_layout(xaxis_title="ano", yaxis_title="% dos títulos"))

    seasons = q("SELECT * FROM analytics.mart_season_trends ORDER BY season_key DESC LIMIT 16")
    if not seasons.empty:
        st.subheader("Últimas temporadas")
        st.dataframe(seasons, width="stretch", hide_index=True)

# ---------------------------------------------------------------- polarização
with tabs[3]:
    pol = q("SELECT * FROM analytics.mart_polarizing_anime")
    if not pol.empty:
        fig = px.scatter(pol, x="mean_score", y="polarization_index", hover_name="title",
                         hover_data=["share_9_10", "share_1_4", "total_votes"], color_discrete_sequence=[BLUE],
                         title="Nota média × polarização — o canto superior é o 'ame ou odeie'")  # fmt: skip
        fig.update_traces(marker=dict(size=9, line=dict(width=2, color="rgba(255,255,255,0.9)")))
        show(style(fig).update_layout(xaxis_title="nota média", yaxis_title="índice de polarização (0–1)"))
        st.subheader("Mais polarizadores")
        st.dataframe(pol.sort_values("polarization_rank").head(20), width="stretch", hide_index=True)
    st.subheader("Joias escondidas")
    st.caption("Nota bayesiana no quartil superior e poucos membros.")
    st.dataframe(
        q("SELECT * EXCLUDE (mal_url) FROM analytics.mart_hidden_gems ORDER BY gem_score DESC LIMIT 30"),
        width="stretch",
        hide_index=True,
    )

# ---------------------------------------------------------------- franquias
with tabs[4]:
    fr = q("SELECT * FROM analytics.mart_franchise_summary ORDER BY total_members DESC")
    if not fr.empty:
        top = fr.head(20).sort_values("score_change_first_to_latest")
        colors = [BLUE if v >= 0 else RED for v in top.score_change_first_to_latest]
        fig = go.Figure(go.Bar(x=top.score_change_first_to_latest, y=top.franchise_name, orientation="h",
                               marker_color=colors, customdata=top[["first_entry_score", "latest_entry_score"]],
                               hovertemplate="%{y}<br>primeira: %{customdata[0]:.2f} → "
                                             "última: %{customdata[1]:.2f}<extra></extra>"))  # fmt: skip
        fig.update_layout(title="Melhorou ou piorou? Nota da última entrada − primeira (20 maiores franquias)")
        show(style(fig, 560).update_layout(xaxis_title="variação de nota", yaxis_title=None))
        st.dataframe(fr, width="stretch", hide_index=True)

# ---------------------------------------------------------------- em alta
with tabs[5]:
    tr = q("SELECT * FROM analytics.mart_anime_trending ORDER BY members_gained DESC LIMIT 30")
    if tr.empty:
        st.info("Precisa de pelo menos duas extrações do mesmo anime em dias diferentes.")
    else:
        st.caption(f"Comparando {tr.snapshot_date.max():%d/%m} com a extração anterior de cada anime.")
        st.dataframe(tr, width="stretch", hide_index=True)

# ---------------------------------------------------------------- abandono
with tabs[6]:
    dr = q("SELECT * FROM analytics.mart_drop_rate_by_genre ORDER BY drop_rate")
    if not dr.empty:
        fig = px.bar(dr, x="drop_rate", y="genre_name", orientation="h", color_discrete_sequence=[BLUE],
                     hover_data=["num_interactions", "avg_score_when_completed", "avg_score_when_dropped"],
                     title="Que gêneros as pessoas mais abandonam? (dropped / (completed + dropped))")  # fmt: skip
        fig.update_xaxes(tickformat=".0%")
        show(style(fig, 480).update_layout(xaxis_title="taxa de abandono", yaxis_title=None))

# ---------------------------------------------------------------- meu perfil
with tabs[7]:
    users = q("SELECT DISTINCT username FROM core.fct_my_list ORDER BY 1")
    if users.empty:
        st.info("Configure MAL_USERNAME no .env e rode `malpipe my-list`.")
    else:
        user = st.selectbox("Usuário", users.username.tolist())
        overall = q(
            "SELECT * FROM analytics.mart_my_profile_vs_mal WHERE username = ? AND dimension = 'overall'", (user,)
        )
        mine = q("SELECT * FROM core.fct_my_list WHERE username = ?", (user,))
        if not overall.empty:
            o = overall.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Títulos avaliados", int(o.num_titles))
            c2.metric("Sua média", f"{o.my_avg_score:.2f}")
            c3.metric("Média do MAL nesses títulos", f"{o.mal_avg_score:.2f}", f"{o.delta_avg:+.2f} você")
            c4.metric("Horas assistidas", f"{mine.hours_watched.sum():,.0f}".replace(",", "."))

        dim = st.radio("Recorte", ["genre", "studio", "decade", "media_type"], horizontal=True,
                       format_func={"genre": "Gênero", "studio": "Estúdio", "decade": "Década",
                                    "media_type": "Formato"}.get)  # fmt: skip
        prof = q(
            """SELECT * FROM analytics.mart_my_profile_vs_mal
               WHERE username = ? AND dimension = ? AND num_titles >= 3 ORDER BY delta_avg""",
            (user, dim),
        )
        if not prof.empty:
            colors = [BLUE if v >= 0 else RED for v in prof.delta_avg]
            fig = go.Figure(go.Bar(x=prof.delta_avg, y=prof.value, orientation="h", marker_color=colors,
                                   customdata=prof[["my_avg_score", "mal_avg_score", "num_titles"]],
                                   hovertemplate="%{y}<br>você %{customdata[0]:.2f} · MAL %{customdata[1]:.2f}"
                                                 "<br>%{customdata[2]} títulos<extra></extra>"))  # fmt: skip
            fig.add_vline(x=0, line_color=NEUTRAL, line_width=1)
            fig.update_layout(title="Onde você é mais generoso (azul) ou mais crítico (vermelho) que o MAL")
            show(style(fig, max(320, 28 * len(prof))).update_layout(xaxis_title="sua nota − nota do MAL",
                                                                    yaxis_title=None))  # fmt: skip

        scored = mine.dropna(subset=["user_score", "mal_mean_score"])
        if not scored.empty:
            fig = px.scatter(scored, x="mal_mean_score", y="user_score", hover_name="title",
                             color_discrete_sequence=[BLUE], title="Sua nota × nota do MAL")  # fmt: skip
            fig.update_traces(marker=dict(size=9, opacity=0.8, line=dict(width=2, color="rgba(255,255,255,0.9)")))
            fig.add_shape(type="line", x0=1, y0=1, x1=10, y1=10, line=dict(color=NEUTRAL, dash="dot", width=1))
            show(style(fig).update_layout(xaxis_title="média do MAL", yaxis_title="sua nota"))
            st.subheader("Maiores divergências")
            st.dataframe(
                scored.reindex(scored.score_delta.abs().sort_values(ascending=False).index)[
                    ["title", "user_score", "mal_mean_score", "score_delta", "main_studio_name", "season_year"]
                ].head(20),
                width="stretch",
                hide_index=True,
            )

# ---------------------------------------------------------------- recomendações
with tabs[8]:
    metrics = q("SELECT * FROM ml.model_metrics")
    recs = q("SELECT * FROM ml.recommendations_for_user WHERE model = 'hybrid' ORDER BY username, rank")
    if not recs.empty:
        st.subheader("Recomendado para você")
        st.dataframe(
            recs[["username", "rank", "title", "because_you_liked", "already_in_plan_to_watch"]],
            width="stretch",
            hide_index=True,
        )
    if not metrics.empty:
        st.subheader("Avaliação offline dos modelos")
        st.caption(
            "Holdout: escondemos 20% dos itens com nota ≥ 8 de cada usuário e medimos se o modelo os reencontra."
        )
        cols = [c for c in metrics.columns if c.startswith(("precision", "recall", "ndcg"))] + [
            "catalog_coverage", "avg_popularity_percentile"]  # fmt: skip
        st.dataframe(metrics[["model", *cols]], width="stretch", hide_index=True)
        ndcg_col = next(c for c in metrics.columns if c.startswith("ndcg"))
        fig = px.bar(metrics.sort_values(ndcg_col), x=ndcg_col, y="model", orientation="h",
                     color_discrete_sequence=[BLUE], title="NDCG@k por modelo", text_auto=".3f")  # fmt: skip
        show(style(fig, 300).update_layout(yaxis_title=None))

    titles = q(
        "SELECT DISTINCT a.title, s.mal_id FROM ml.similar_anime s JOIN core.dim_anime a USING (mal_id) ORDER BY 1"
    )
    if not titles.empty:
        st.subheader("Animes parecidos (item-kNN)")
        choice = st.selectbox("Escolha um anime", titles.title.tolist())
        mal_id = int(titles.loc[titles.title == choice, "mal_id"].iloc[0])
        st.dataframe(
            q("SELECT rank, similar_title, similarity FROM ml.similar_anime WHERE mal_id = ? ORDER BY rank", (mal_id,)),
            width="stretch",
            hide_index=True,
        )
