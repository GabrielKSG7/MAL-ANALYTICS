"""MAL Analytics — dashboard.

    streamlit run dashboard/app.py      (ou .\\scripts\\tasks.ps1 dashboard)

Duas camadas:
- Painel executivo: KPIs e poucos gráficos bem escolhidos por tema, com texto explicando cada número.
- Explorar: filtros globais (barra lateral) + gráfico e tabela livres, com download.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from lib import (
    AQUA,
    BLUE,
    DB_PATH,
    DEFAULT_USER,
    GRAY,
    MEDIA_LABELS,
    ORANGE,
    RED,
    SOURCE_COLORS,
    STATUS_COLORS,
    STATUS_LABELS,
    Filters,
    db_available,
    empty_state,
    fmt_compact,
    fmt_dec,
    fmt_int,
    fmt_pct,
    poster_columns,
    q,
    show,
    sidebar_filters,
    style,
    table_exists,
)

st.set_page_config(page_title="MAL Analytics", page_icon="📺", layout="wide")

SOURCE_CASE = """
    CASE
        WHEN a.source_material = 'original' THEN 'Original'
        WHEN a.source_material IN ('manga', 'web_manga', '4_koma_manga') THEN 'Mangá'
        WHEN a.source_material IN ('light_novel', 'web_novel') THEN 'Light novel'
        ELSE 'Outras'
    END
"""


def kpi_row(items: list[tuple[str, str, str | None, str | None]]) -> None:
    """items: (rótulo, valor, delta, ajuda)."""
    cols = st.columns(len(items))
    for col, (label, value, delta, help_) in zip(cols, items, strict=True):
        col.metric(label, value, delta, help=help_, border=True)


# =============================================================================== cabeçalho
if not db_available():
    st.error(f"Banco não encontrado em `{DB_PATH}`. Rode `malpipe sample` + build, ou a carga real.")
    st.stop()

is_sample = not q("SELECT 1 FROM meta.runs WHERE command = 'sample' LIMIT 1").empty
last = q("SELECT max(last_extracted_at) AS ts, count(*) AS n FROM core.dim_anime")
if last.empty or not last.n[0]:
    st.error("A tabela core.dim_anime está vazia. Rode a ingestão e depois o build do dbt.")
    st.stop()

st.title("📺 MAL Analytics")
st.caption(
    f"{fmt_int(last.n[0])} animes do MyAnimeList · atualizado em {pd.to_datetime(last.ts[0]):%d/%m/%Y} · "
    "MAL API · Jikan · anime-offline-database · Kaggle → DuckDB + dbt"
    + (" · ⚠️ **dados sintéticos de demonstração**" if is_sample else "")
)

flt: Filters = sidebar_filters()
WHERE, PARAMS = flt.where("a")

tabs = st.tabs(
    [
        "🏠 Visão geral",
        "👤 Meu perfil",
        "🎬 Estúdios",
        "📈 Tendências",
        "🧬 Franquias",
        "💎 Descobrir",
        "🎯 Recomendações",
        "🔎 Explorar",
        "🛠️ Pipeline",
    ]  # fmt: skip
)

# =============================================================================== 1. visão geral
with tabs[0]:
    st.caption(f"Recorte: {flt.describe()}")
    k = q(
        f"""SELECT count(*) n, count(mean_score) n_scored, avg(mean_score) avg_s, median(mean_score) med_s,
                   avg(CASE WHEN mean_score >= 8 THEN 1.0 WHEN mean_score IS NOT NULL THEN 0.0 END) share8,
                   count(DISTINCT main_studio_id) studios, max(num_list_users) top_members
            FROM core.dim_anime a WHERE {WHERE}""",
        PARAMS,
    ).iloc[0]
    kpi_row(
        [
            ("Animes", fmt_int(k.n), None, "Títulos no recorte dos filtros."),
            ("Nota média", fmt_dec(k.avg_s), None, f"Mediana: {fmt_dec(k.med_s)}"),
            ("Nota ≥ 8", fmt_pct(k.share8, 1), None, "Fatia dos títulos com nota média 8 ou mais."),
            ("Estúdios", fmt_int(k.studios), None, "Estúdios principais distintos no recorte."),
            ("Maior audiência", fmt_compact(k.top_members), None, "Membros do anime mais popular."),
        ]
    )

    left, right = st.columns(2)
    with left:
        mix = q(
            f"""SELECT a.season_year AS ano, {SOURCE_CASE} AS origem, count(*) AS titulos
                FROM core.dim_anime a WHERE {WHERE} GROUP BY ALL ORDER BY ano""",
            PARAMS,
        )
        if not mix.empty:
            fig = px.bar(
                mix, x="ano", y="titulos", color="origem", color_discrete_map=SOURCE_COLORS,
                category_orders={"origem": list(SOURCE_COLORS)},
                title="Lançamentos por ano e origem", labels={"titulos": "títulos", "ano": ""},
            )  # fmt: skip
            fig.update_traces(marker_line_width=0)
            show(style(fig))
    with right:
        infl = q(
            f"""SELECT a.season_year AS ano, avg(mean_score) media,
                       quantile_cont(mean_score, 0.1) p10, quantile_cont(mean_score, 0.9) p90, count(*) n
                FROM core.dim_anime a WHERE {WHERE} AND mean_score IS NOT NULL
                GROUP BY 1 HAVING count(*) >= 5 ORDER BY 1""",
            PARAMS,
        )
        if not infl.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=infl.ano, y=infl.p90, line=dict(width=0), hoverinfo="skip", showlegend=False))
            fig.add_trace(
                go.Scatter(
                    x=infl.ano,
                    y=infl.p10,
                    fill="tonexty",
                    line=dict(width=0),
                    name="10% a 90% dos títulos",
                    fillcolor="rgba(42,120,214,0.16)",
                    hoverinfo="skip",
                )  # fmt: skip
            )
            fig.add_trace(
                go.Scatter(
                    x=infl.ano,
                    y=infl.media,
                    name="nota média",
                    mode="lines",
                    line=dict(color=BLUE, width=2),
                    customdata=infl[["p10", "p90", "n"]],
                    hovertemplate="<b>%{x}</b><br>média %{y:.2f}<br>faixa %{customdata[0]:.2f}–%{customdata[1]:.2f}"
                    "<br>%{customdata[2]} títulos<extra></extra>",
                )  # fmt: skip
            )
            fig.update_layout(title="As notas estão subindo?", hovermode="x unified")
            show(style(fig))

    left, right = st.columns(2)
    with left:
        hist = q(f"SELECT mean_score FROM core.dim_anime a WHERE {WHERE} AND mean_score IS NOT NULL", PARAMS)
        if not hist.empty:
            fig = px.histogram(hist, x="mean_score", nbins=45, color_discrete_sequence=[BLUE],
                               title="Distribuição das notas médias", labels={"mean_score": "nota média"})  # fmt: skip
            fig.add_vline(x=hist.mean_score.median(), line_dash="dot", line_color=GRAY,
                          annotation_text=f"mediana {fmt_dec(hist.mean_score.median())}")  # fmt: skip
            show(style(fig, legend=False).update_layout(yaxis_title="títulos", bargap=0.06))
    with right:
        fmt_df = q(
            f"""SELECT media_type, count(*) n, avg(mean_score) nota FROM core.dim_anime a WHERE {WHERE}
                GROUP BY 1 ORDER BY n""",
            PARAMS,
        )
        if not fmt_df.empty:
            fmt_df["formato"] = fmt_df.media_type.map(lambda m: MEDIA_LABELS.get(m, m))
            fig = px.bar(fmt_df, x="n", y="formato", orientation="h", color_discrete_sequence=[BLUE], text="n",
                         custom_data=["nota"], title="Títulos por formato")  # fmt: skip
            fig.update_traces(hovertemplate="%{y}: %{x} títulos<br>nota média %{customdata[0]:.2f}<extra></extra>",
                              textposition="outside", cliponaxis=False)  # fmt: skip
            show(style(fig, legend=False).update_layout(xaxis_title=None, yaxis_title=None))

    st.subheader("🏆 Top 10 do recorte")
    st.caption("Ordenado pela nota bayesiana (penaliza títulos com poucos votos): WR = v/(v+m)·R + m/(v+m)·C")
    top = q(
        f"""SELECT picture_url, title, season_year, main_studio_name, genres_label, mean_score, weighted_score,
                   num_list_users, mal_url
            FROM core.dim_anime a WHERE {WHERE} AND weighted_score IS NOT NULL
            ORDER BY weighted_score DESC LIMIT 10""",
        PARAMS,
    )
    st.dataframe(top, column_config=poster_columns(), hide_index=True, width="stretch", row_height=70)

# =============================================================================== 2. meu perfil
with tabs[1]:
    users = q("SELECT DISTINCT username FROM core.fct_my_list ORDER BY 1")
    if users.empty:
        empty_state("Configure MAL_USERNAME no .env e rode `malpipe my-list` + build.")
    else:
        opts = users.username.tolist()
        user = st.selectbox("Usuário", opts, index=opts.index(DEFAULT_USER) if DEFAULT_USER in opts else 0)
        mine = q(
            """SELECT l.*, a.picture_url, a.mal_url FROM core.fct_my_list l
               LEFT JOIN core.dim_anime a USING (mal_id) WHERE l.username = ?""",
            (user,),
        )
        scored = mine.dropna(subset=["user_score", "mal_mean_score"])
        counts = mine.list_status.value_counts()
        kpi_row(
            [
                ("Completos", fmt_int(counts.get("completed", 0)), None, None),
                (
                    "Horas assistidas",
                    fmt_int(mine.hours_watched.sum()),
                    None,
                    f"≈ {fmt_int(mine.hours_watched.sum() / 24)} dias seguidos",
                ),  # fmt: skip
                (
                    "Sua nota média",
                    fmt_dec(scored.user_score.mean()),
                    f"{scored.score_delta.mean():+.2f} vs MAL".replace(".", ","),
                    "Média das suas notas menos a média do MAL nos mesmos títulos.",
                ),  # fmt: skip
                (
                    "Correlação c/ MAL",
                    fmt_dec(scored.user_score.corr(scored.mal_mean_score)),
                    None,
                    "Correlação entre a sua nota e a do MAL (1 = idêntica, 0 = nenhuma relação).",
                ),  # fmt: skip
                ("Plan to watch", fmt_int(counts.get("plan_to_watch", 0)), None, None),
                ("Abandonados", fmt_int(counts.get("dropped", 0)), None, None),
            ]
        )

        left, right = st.columns(2)
        with left:
            you = scored.user_score.round().value_counts().reindex(range(1, 11), fill_value=0)
            mal = scored.mal_mean_score.round().clip(1, 10).value_counts().reindex(range(1, 11), fill_value=0)
            fig = go.Figure()
            fig.add_bar(x=list(range(1, 11)), y=you.values, name="suas notas", marker_color=BLUE)
            fig.add_bar(x=list(range(1, 11)), y=mal.values, name="nota do MAL (arredondada)", marker_color=ORANGE)
            fig.update_layout(title="Como você distribui as notas × a comunidade", barmode="group",
                              xaxis=dict(dtick=1, title="nota"), yaxis_title="títulos")  # fmt: skip
            show(style(fig))
        with right:
            st_df = (
                mine.list_status.value_counts().rename_axis("status").reset_index(name="n")
                .assign(rotulo=lambda d: d.status.map(STATUS_LABELS))
                .sort_values("n")
            )  # fmt: skip
            fig = px.bar(st_df, x="n", y="rotulo", orientation="h", color="status", text="n",
                         color_discrete_map=STATUS_COLORS, title="Sua lista por status")  # fmt: skip
            fig.update_traces(textposition="outside", cliponaxis=False)
            show(style(fig, legend=False).update_layout(xaxis_title=None, yaxis_title=None))

        st.subheader("Onde você é mais generoso ou mais crítico que o MAL")
        c1, c2 = st.columns([3, 1])
        dim = c1.radio(
            "Recorte", ["genre", "studio", "decade", "media_type"], horizontal=True,
            format_func={"genre": "Gênero", "studio": "Estúdio", "decade": "Década", "media_type": "Formato"}.get,
        )  # fmt: skip
        min_n = c2.slider("Mínimo de títulos", 1, 30, 5)
        prof = q(
            """SELECT * FROM analytics.mart_my_profile_vs_mal
               WHERE username = ? AND dimension = ? AND num_titles >= ? ORDER BY delta_avg""",
            (user, dim, min_n),
        )
        if prof.empty:
            empty_state("Nenhum grupo com títulos suficientes — diminua o mínimo.")
        else:
            if dim == "media_type":
                prof["value"] = prof.value.map(lambda m: MEDIA_LABELS.get(m, m))
            colors = [BLUE if v >= 0 else RED for v in prof.delta_avg]
            fig = go.Figure(
                go.Bar(
                    x=prof.delta_avg,
                    y=prof.value,
                    orientation="h",
                    marker_color=colors,
                    customdata=prof[["my_avg_score", "mal_avg_score", "num_titles"]],
                    hovertemplate="<b>%{y}</b><br>você %{customdata[0]:.2f} · MAL %{customdata[1]:.2f}"
                    "<br>%{customdata[2]} títulos<extra></extra>",
                )  # fmt: skip
            )
            fig.add_vline(x=0, line_color=GRAY, line_width=1)
            fig.update_layout(title="Sua nota − nota do MAL (azul: você gosta mais · vermelho: você gosta menos)")
            show(style(fig, max(320, 24 * len(prof)), legend=False).update_layout(yaxis_title=None))

        left, right = st.columns(2)
        with left:
            fig = px.scatter(scored, x="mal_mean_score", y="user_score", hover_name="title",
                             color_discrete_sequence=[BLUE], opacity=0.55,
                             title="Cada ponto é um anime: sua nota × nota do MAL",
                             labels={"mal_mean_score": "nota do MAL", "user_score": "sua nota"})  # fmt: skip
            fig.update_traces(marker=dict(size=9, line=dict(width=1, color="rgba(255,255,255,0.8)")))
            fig.add_shape(type="line", x0=1, y0=1, x1=10, y1=10, line=dict(color=GRAY, dash="dot", width=1))
            show(style(fig, 420, legend=False))
        with right:
            done = mine.dropna(subset=["finished_on"]).assign(
                mes=lambda d: pd.to_datetime(d.finished_on).dt.to_period("M")
            )
            if done.empty:
                empty_state("Sua lista não tem datas de término preenchidas no MAL.")
            else:
                per = done.groupby("mes").agg(titulos=("mal_id", "count"), horas=("hours_watched", "sum")).reset_index()
                per["mes"] = per.mes.dt.to_timestamp()
                fig = px.bar(per, x="mes", y="titulos", color_discrete_sequence=[BLUE], custom_data=["horas"],
                             title="Animes terminados por mês", labels={"mes": "", "titulos": "títulos"})  # fmt: skip
                fig.update_traces(hovertemplate="%{x|%b/%Y}: %{y} títulos · %{customdata[0]:.0f} h<extra></extra>")
                show(style(fig, 420, legend=False))

        st.subheader("Maiores divergências")
        a, b = st.columns(2)
        cols = ["picture_url", "title", "user_score", "mal_mean_score", "score_delta", "mal_url"]
        cfg = poster_columns(
            {
                "user_score": st.column_config.NumberColumn("Sua nota", format="%d"),
                "mal_mean_score": st.column_config.NumberColumn("MAL", format="%.2f"),
                "score_delta": st.column_config.NumberColumn("Diferença", format="%+.2f"),
            }
        )
        a.markdown("**Você amou, o MAL nem tanto**")
        a.dataframe(scored.nlargest(8, "score_delta")[cols], column_config=cfg, hide_index=True, row_height=64)
        b.markdown("**O MAL ama, você não**")
        b.dataframe(scored.nsmallest(8, "score_delta")[cols], column_config=cfg, hide_index=True, row_height=64)

# =============================================================================== 3. estúdios
with tabs[2]:
    studios = q("SELECT * FROM analytics.mart_studio_performance")
    if studios.empty:
        empty_state("Sem dados de estúdios ainda.")
    else:
        c1, c2 = st.columns([2, 1])
        metric = c1.radio(
            "Ordenar por",
            ["median_score", "vote_weighted_score", "share_titles_8_plus", "total_members", "num_titles"],
            horizontal=True,
            format_func={
                "median_score": "Mediana da nota",
                "vote_weighted_score": "Nota ponderada por votos",
                "share_titles_8_plus": "% de títulos ≥ 8",
                "total_members": "Alcance (membros)",
                "num_titles": "Volume de títulos",
            }.get,
        )
        min_titles = c2.slider("Mínimo de títulos", 5, 150, 30, step=5)
        base = studios[studios.num_titles >= min_titles]
        st.caption(
            "Por que várias métricas? A nota ponderada por votos é puxada pelos sucessos (ex.: um filme "
            "gigante); a mediana mostra o título típico do estúdio; o desvio-padrão mostra a consistência."
        )
        left, right = st.columns([3, 2])
        with left:
            top = base.nlargest(15, metric).sort_values(metric)
            fig = px.bar(top, x=metric, y="studio_name", orientation="h", color_discrete_sequence=[BLUE],
                         hover_data={"num_titles": True, "best_title": True, "median_score": ":.2f"},
                         title=f"Top 15 estúdios ({len(base)} com {min_titles}+ títulos)")  # fmt: skip
            if metric in ("median_score", "vote_weighted_score"):
                fig.update_xaxes(range=[top[metric].min() - 0.3, top[metric].max() + 0.1])
            if metric == "share_titles_8_plus":
                fig.update_xaxes(tickformat=".0%")
            show(style(fig, 520, legend=False).update_layout(xaxis_title=None, yaxis_title=None))
        with right:
            fig = px.scatter(base, x="score_stddev", y="median_score", size="num_titles", hover_name="studio_name",
                             color_discrete_sequence=[BLUE], size_max=40,
                             hover_data={"num_titles": True, "best_title": True},
                             title="Qualidade típica × consistência",
                             labels={"score_stddev": "variação entre títulos (menor = mais consistente)",
                                     "median_score": "mediana da nota"})  # fmt: skip
            fig.update_traces(marker=dict(opacity=0.6, line=dict(width=1, color="rgba(255,255,255,0.9)")))
            show(style(fig, 520, legend=False))

        st.subheader("Raio-X de um estúdio")
        names = base.sort_values("total_members", ascending=False).studio_name.tolist()
        name = st.selectbox("Estúdio", names)
        s = base[base.studio_name == name].iloc[0]
        kpi_row(
            [
                ("Títulos", fmt_int(s.num_titles), None, f"{int(s.first_year)}–{int(s.last_year)}"),
                ("Mediana da nota", fmt_dec(s.median_score), None, None),
                ("Títulos ≥ 8", fmt_pct(s.share_titles_8_plus), None, None),
                ("Consistência", f"#{int(s.consistency_rank)}", None, f"desvio-padrão {fmt_dec(s.score_stddev)}"),
                ("Melhor título", s.best_title[:28] + ("…" if len(s.best_title) > 28 else ""), None, s.best_title),
            ]
        )
        works = q(
            """SELECT picture_url, title, season_year, media_type, mean_score, num_list_users, mal_url
               FROM core.dim_anime WHERE main_studio_name = ? AND mean_score IS NOT NULL ORDER BY season_year""",
            (name,),
        )
        left, right = st.columns([3, 2])
        with left:
            fig = px.scatter(works, x="season_year", y="mean_score", size="num_list_users", hover_name="title",
                             color_discrete_sequence=[BLUE], size_max=35, title=f"Obras da {name} ao longo do tempo",
                             labels={"season_year": "", "mean_score": "nota"})  # fmt: skip
            fig.update_traces(marker=dict(opacity=0.6, line=dict(width=1, color="rgba(255,255,255,0.9)")))
            show(style(fig, 420, legend=False))
        with right:
            st.dataframe(works.nlargest(8, "mean_score"), column_config=poster_columns(), hide_index=True,
                         row_height=64, height=420)  # fmt: skip

# =============================================================================== 4. tendências
with tabs[3]:
    st.caption(f"Recorte: {flt.describe()}")
    yearly = q(
        f"""SELECT a.season_year AS ano, {SOURCE_CASE} AS origem, count(*) AS n,
                   sum(CASE WHEN a.is_sequel THEN 1 ELSE 0 END) AS seq
            FROM core.dim_anime a WHERE {WHERE} GROUP BY ALL ORDER BY ano""",
        PARAMS,
    )
    left, right = st.columns(2)
    with left:
        if not yearly.empty:
            fig = px.bar(yearly, x="ano", y="n", color="origem", color_discrete_map=SOURCE_COLORS,
                         category_orders={"origem": list(SOURCE_COLORS)},
                         title="De onde vêm os animes (participação por ano)", labels={"ano": ""})  # fmt: skip
            fig.update_layout(barnorm="percent", yaxis=dict(ticksuffix="%", title=None))
            fig.update_traces(marker_line_width=0, hovertemplate="%{x} · %{fullData.name}: %{y:.0f}%<extra></extra>")
            show(style(fig))
    with right:
        seq = yearly.groupby("ano").agg(n=("n", "sum"), seq=("seq", "sum")).reset_index() if not yearly.empty else None
        if seq is not None:
            seq["share"] = seq.seq / seq.n
            seq = seq[seq.n >= 10]
            fig = px.line(seq, x="ano", y="share", markers=True, color_discrete_sequence=[BLUE],
                          title="Fatia de continuações (sequências) por ano", labels={"ano": ""})  # fmt: skip
            fig.update_traces(line_width=2, marker_size=7, hovertemplate="%{x}: %{y:.0%}<extra></extra>")
            fig.update_yaxes(tickformat=".0%", title=None)
            show(style(fig, legend=False))

    st.subheader("Gêneros ao longo do tempo")
    all_genres = q("SELECT genre_name FROM core.dim_genre ORDER BY num_anime DESC").genre_name.tolist()
    pick = st.multiselect("Compare até 4 gêneros", all_genres, placeholder="Escolha gêneros", default=[g for g in ("Fantasy", "Romance") if g in all_genres],
                          max_selections=4)  # fmt: skip
    if pick:
        gdf = q(
            f"""WITH base AS (SELECT a.season_year AS ano, a.genres FROM core.dim_anime a WHERE {WHERE})
                SELECT ano, g.genre AS genero,
                       avg(CASE WHEN list_contains(genres, g.genre) THEN 1.0 ELSE 0.0 END) AS share
                FROM base CROSS JOIN (SELECT unnest(?::VARCHAR[]) AS genre) g
                GROUP BY ALL HAVING count(*) >= 10 ORDER BY ano""",
            (*PARAMS, tuple(pick)),
        )
        palette = [BLUE, ORANGE, AQUA, "#eda100"]
        fig = px.line(gdf, x="ano", y="share", color="genero", markers=True,
                      color_discrete_map={g: palette[i] for i, g in enumerate(pick)},
                      title="% dos lançamentos do ano que têm o gênero", labels={"ano": ""})  # fmt: skip
        fig.update_traces(line_width=2, marker_size=6)
        fig.update_yaxes(tickformat=".0%", title=None)
        show(style(fig))

    st.subheader("Uma temporada em detalhe")
    seasons = q(
        "SELECT season_key, num_titles, avg_score, top_title, most_popular_title, share_sequels "
        "FROM analytics.mart_season_trends WHERE num_scored > 0 ORDER BY season_key DESC"
    )
    if not seasons.empty:
        sk = st.selectbox("Temporada", seasons.season_key.tolist(),
                          format_func=lambda k: f"{k.split('-')[2].capitalize()} {k.split('-')[0]}")  # fmt: skip
        srow = seasons[seasons.season_key == sk].iloc[0]
        kpi_row(
            [
                ("Títulos (TV/ONA)", fmt_int(srow.num_titles), None, None),
                ("Nota média", fmt_dec(srow.avg_score), None, None),
                ("Continuações", fmt_pct(srow.share_sequels), None, None),
                ("Mais popular", str(srow.most_popular_title)[:26], None, srow.most_popular_title),
            ]
        )
        st.dataframe(
            q(
                """SELECT picture_url, title, media_type, main_studio_name, source_material, mean_score,
                          num_list_users, mal_url
                   FROM core.dim_anime WHERE season_key = ? AND media_type IN ('tv','ona')
                   ORDER BY num_list_users DESC LIMIT 15""",
                (sk,),
            ),
            column_config=poster_columns({"source_material": "Origem"}),
            hide_index=True,
            width="stretch",
            row_height=64,
        )

# =============================================================================== 5. franquias
with tabs[4]:
    fr = q("SELECT * FROM analytics.mart_franchise_summary")
    if fr.empty:
        empty_state("Sem franquias ainda.")
    else:
        big = fr.nlargest(1, "total_runtime_hours").iloc[0]
        changed = fr.dropna(subset=["score_change_first_to_latest"])
        popular = changed[changed.peak_members >= changed.peak_members.quantile(0.9)]
        kpi_row(
            [
                ("Franquias (2+ entradas)", fmt_int(len(fr)), None, None),
                ("Franquia mais longa", f"{fmt_int(big.total_runtime_hours)} h", None, big.franchise_name),
                (
                    "Melhoram na última temp.",
                    fmt_pct((popular.score_change_first_to_latest > 0).mean()),
                    None,
                    "Entre as 10% mais populares: última temporada de TV com nota maior que a primeira.",
                ),  # fmt: skip
                (
                    "Variação mediana",
                    fmt_dec(popular.score_change_first_to_latest.median()),
                    None,
                    "Última − primeira temporada de TV, nas franquias mais populares.",
                ),  # fmt: skip
            ]
        )
        left, right = st.columns(2)
        with left:
            top = changed.nlargest(20, "peak_members").sort_values("score_change_first_to_latest")
            colors = [BLUE if v >= 0 else RED for v in top.score_change_first_to_latest]
            fig = go.Figure(
                go.Bar(
                    x=top.score_change_first_to_latest,
                    y=top.franchise_name,
                    orientation="h",
                    marker_color=colors,
                    customdata=top[["first_tv_entry", "first_entry_score", "latest_tv_entry", "latest_entry_score"]],
                    hovertemplate="<b>%{y}</b><br>%{customdata[0]}: %{customdata[1]:.2f}"
                    "<br>%{customdata[2]}: %{customdata[3]:.2f}<extra></extra>",
                )  # fmt: skip
            )
            fig.add_vline(x=0, line_color=GRAY, line_width=1)
            fig.update_layout(title="Melhorou ou piorou? Última − primeira temporada de TV (20 maiores)")
            show(style(fig, 560, legend=False).update_layout(yaxis_title=None))
        with right:
            longest = fr.nlargest(15, "total_runtime_hours").sort_values("total_runtime_hours")
            fig = px.bar(longest, x="total_runtime_hours", y="franchise_name", orientation="h",
                         color_discrete_sequence=[BLUE], hover_data=["num_entries", "total_episodes"],
                         title="Para maratonar: franquias mais longas (horas)")  # fmt: skip
            show(style(fig, 560, legend=False).update_layout(xaxis_title=None, yaxis_title=None))

        st.subheader("Linha do tempo de uma franquia")
        fname = st.selectbox("Franquia", fr.sort_values("total_members", ascending=False).franchise_name.tolist())
        fid = int(fr[fr.franchise_name == fname].franchise_id.iloc[0])
        ent = q(
            """SELECT picture_url, title, start_date, media_type, num_episodes, mean_score, num_list_users, mal_url
               FROM core.dim_anime WHERE franchise_id = ? ORDER BY start_date""",
            (fid,),
        )
        scored_ent = ent.dropna(subset=["mean_score", "start_date"])
        if not scored_ent.empty:
            scored_ent = scored_ent.assign(formato=scored_ent.media_type.map(lambda m: MEDIA_LABELS.get(m, m)))
            fig = px.scatter(scored_ent, x="start_date", y="mean_score", size="num_list_users", color="formato",
                             hover_name="title", size_max=30, title=f"{fname}: nota de cada entrada",
                             color_discrete_sequence=[BLUE, ORANGE, AQUA, "#eda100", "#e87ba4"],
                             labels={"start_date": "", "mean_score": "nota"})  # fmt: skip
            tv = scored_ent[scored_ent.media_type == "tv"]
            if len(tv) >= 2:
                fig.add_trace(go.Scatter(x=tv.start_date, y=tv.mean_score, mode="lines", name="temporadas de TV",
                                         line=dict(color=BLUE, width=1.5, dash="dot"), hoverinfo="skip"))  # fmt: skip
            show(style(fig, 400))
        st.dataframe(ent, column_config=poster_columns({"start_date": st.column_config.DateColumn("Estreia")}),
                     hide_index=True, width="stretch", row_height=56)  # fmt: skip

# =============================================================================== 6. descobrir
with tabs[5]:
    st.subheader("💎 Joias escondidas")
    st.caption("Nota no topo entre títulos com 1.000+ votos, mas com poucos membros. Boas descobertas.")
    gems = q("SELECT g.*, a.picture_url FROM analytics.mart_hidden_gems g JOIN core.dim_anime a USING (mal_id)")
    if gems.empty:
        empty_state("Nenhuma joia com os critérios atuais (veja `hidden_gem_*` no dbt_project.yml).")
    else:
        gg = st.multiselect(
            "Filtrar por gênero",
            sorted({g for s in gems.genres_label.dropna() for g in s.split(", ")}),
            placeholder="Todos",
        )
        view = gems[gems.genres_label.fillna("").apply(lambda s: all(g in s for g in gg))] if gg else gems
        st.dataframe(
            view.sort_values("mean_score", ascending=False)[
                ["picture_url", "title", "media_type", "season_year", "main_studio_name", "genres_label", "mean_score",
                 "num_list_users", "mal_url"]  # fmt: skip
            ],
            column_config=poster_columns(), hide_index=True, width="stretch", row_height=64, height=480,
        )  # fmt: skip

    left, right = st.columns(2)
    with left:
        st.subheader("⚖️ Ame ou odeie")
        pol = q("SELECT * FROM analytics.mart_polarizing_anime ORDER BY polarization_rank LIMIT 20")
        if pol.empty:
            empty_state("Depende da distribuição de notas do Jikan: rode `malpipe jikan statistics` + build.")
        else:
            fig = px.bar(pol.sort_values("polarization_index"), x="polarization_index", y="title", orientation="h",
                         color_discrete_sequence=[BLUE], hover_data=["mean_score", "share_9_10", "share_1_4"],
                         title="Mais polarizadores (0 = consenso, 1 = metade ama / metade odeia)")  # fmt: skip
            show(style(fig, 520, legend=False).update_layout(yaxis_title=None, xaxis_title=None))
    with right:
        st.subheader("🔥 Em alta")
        tr = q("SELECT * FROM analytics.mart_anime_trending ORDER BY members_gained DESC LIMIT 15")
        if tr.empty:
            empty_state("Aparece a partir da 2ª extração semanal (`malpipe incremental` + build).")
        else:
            fig = px.bar(tr.sort_values("members_gained"), x="members_gained", y="title", orientation="h",
                         color_discrete_sequence=[BLUE], hover_data=["score_change", "days_between"],
                         title="Mais membros ganhos desde a extração anterior")  # fmt: skip
            show(style(fig, 520, legend=False).update_layout(yaxis_title=None, xaxis_title=None))

    drop = q("SELECT * FROM analytics.mart_drop_rate_by_genre WHERE num_interactions >= 100 ORDER BY drop_rate")
    if not drop.empty:
        st.subheader("🚪 O que as pessoas mais abandonam")
        fig = px.bar(drop, x="drop_rate", y="genre_name", orientation="h", color_discrete_sequence=[BLUE],
                     title="Taxa de abandono por gênero (Kaggle)")  # fmt: skip
        fig.update_xaxes(tickformat=".0%")
        show(style(fig, 520, legend=False).update_layout(xaxis_title=None, yaxis_title=None))

# =============================================================================== 7. recomendações
with tabs[6]:
    recs = q(
        """SELECT r.*, a.picture_url, a.mal_url, a.mean_score, a.genres_label, a.season_year
           FROM ml.recommendations_for_user r LEFT JOIN core.dim_anime a USING (mal_id)
           WHERE r.model = (SELECT CASE WHEN bool_or(model = 'hybrid') THEN 'hybrid' ELSE any_value(model) END
                            FROM ml.recommendations_for_user)
           ORDER BY r.rank"""
    )
    if recs.empty:
        empty_state("Rode `malpipe recommend` (ou o build completo).")
    else:
        model_name = {"hybrid": "híbrido (colaborativo + conteúdo + popularidade)", "content": "de conteúdo"}
        share_ptw = recs.already_in_plan_to_watch.head(20).mean()
        kpi_row(
            [
                (
                    "Modelo",
                    model_name.get(recs.model.iloc[0], recs.model.iloc[0]).split(" (")[0],
                    None,
                    model_name.get(recs.model.iloc[0]),
                ),  # fmt: skip
                (
                    "Top 20 já no seu plan-to-watch",
                    fmt_pct(share_ptw),
                    None,
                    "Quanto o modelo concorda com o que você já queria ver.",
                ),  # fmt: skip
                ("Nota média do top 20", fmt_dec(recs.head(20).mean_score.mean()), None, None),
            ]
        )
        only_new = st.toggle("Só descobertas (esconder o que já está no plan-to-watch)", value=False)
        shown = recs[~recs.already_in_plan_to_watch] if only_new else recs
        shown = shown.head(30).assign(posicao=lambda d: range(1, len(d) + 1))
        st.dataframe(
            shown[
                [
                    "posicao",
                    "picture_url",
                    "title",
                    "because_you_liked",
                    "mean_score",
                    "genres_label",
                    "already_in_plan_to_watch",
                    "mal_url",
                ]
            ],  # fmt: skip
            column_config=poster_columns(
                {
                    "posicao": st.column_config.NumberColumn("#", width="small"),
                    "because_you_liked": st.column_config.TextColumn("Porque você gostou de", width="medium"),
                    "already_in_plan_to_watch": st.column_config.CheckboxColumn("No PTW"),
                }
            ),
            hide_index=True,
            width="stretch",
            row_height=70,
            height=620,
        )

    metrics = q("SELECT * FROM ml.model_metrics")
    if not metrics.empty:
        st.subheader("Avaliação offline dos modelos")
        ndcg = next(c for c in metrics.columns if c.startswith("ndcg"))
        fig = px.scatter(metrics, x="catalog_coverage", y=ndcg, text="model", size_max=20,
                         color_discrete_sequence=[BLUE], title="Acerto (NDCG) × variedade (cobertura do catálogo)")  # fmt: skip
        fig.update_traces(marker_size=14, textposition="top center")
        fig.update_xaxes(tickformat=".0%")
        show(style(fig, 380, legend=False))

# =============================================================================== 8. explorar
with tabs[7]:
    st.caption(f"Recorte da barra lateral: {flt.describe()}")
    c1, c2, c3 = st.columns([2, 1, 1])
    search = c1.text_input("Buscar título (japonês ou inglês)", placeholder="ex.: frieren, gundam, ghibli…")
    order = c2.selectbox("Ordenar por", ["weighted_score", "mean_score", "num_list_users", "season_year"],
                         format_func={"weighted_score": "Nota bayesiana", "mean_score": "Nota", "num_list_users":
                                      "Membros", "season_year": "Ano"}.get)  # fmt: skip
    min_score = c3.slider("Nota mínima", 1.0, 10.0, 1.0, 0.25)
    extra = " AND mean_score >= ?"
    params = (*PARAMS, min_score)
    if search:
        extra += " AND (title ILIKE ? OR title_english ILIKE ? OR main_studio_name ILIKE ?)"
        params = (*params, f"%{search}%", f"%{search}%", f"%{search}%")
    data = q(
        f"""SELECT picture_url, title, title_english, season_year, media_type, main_studio_name, source_material,
                   genres_label, mean_score, weighted_score, num_list_users, num_episodes, airing_status, mal_url
            FROM core.dim_anime a WHERE {WHERE} {extra} ORDER BY {order} DESC NULLS LAST""",
        params,
    )
    st.markdown(f"**{fmt_int(len(data))} títulos**")
    if not data.empty:
        fig = px.scatter(data.head(6000), x="num_list_users", y="mean_score", hover_name="title", log_x=True,
                         color_discrete_sequence=[BLUE], opacity=0.45, render_mode="webgl",
                         hover_data={"season_year": True, "main_studio_name": True},
                         title="Popularidade × nota (passe o mouse; escala log no eixo X)",
                         labels={"num_list_users": "membros (log)", "mean_score": "nota"})  # fmt: skip
        show(style(fig, 440, legend=False))
        st.dataframe(data.head(500), column_config=poster_columns({"title_english": "Título em inglês"}),
                     hide_index=True, width="stretch", row_height=56, height=520)  # fmt: skip
        st.download_button("⬇️ Baixar CSV do recorte", data.drop(columns=["picture_url"]).to_csv(index=False).encode(),
                           "mal_recorte.csv", "text/csv")  # fmt: skip

# =============================================================================== 9. pipeline
with tabs[8]:
    st.caption("Saúde da ingestão e cobertura de cada fonte — o lado de engenharia do projeto.")
    cov = q(
        """SELECT
             (SELECT count(DISTINCT mal_id) FROM bronze.mal_anime WHERE http_status = 200) AS mal_ok,
             (SELECT count(*) FROM staging.stg_manami__anime) AS manami,
             (SELECT count(DISTINCT mal_id) FROM bronze.jikan_statistics WHERE http_status = 200) AS jikan_ok,
             (SELECT count(*) FROM bronze.kaggle_animelist) AS kaggle_rows,
             (SELECT count(*) FROM bronze.mal_anime) AS extractions"""
    )
    if not cov.empty:
        c = cov.iloc[0]
        kpi_row(
            [
                ("Animes c/ detalhe (MAL)", fmt_int(c.mal_ok), None, "IDs com extração HTTP 200."),
                (
                    "Cobertura vs manami",
                    fmt_pct(c.mal_ok / c.manami if c.manami else None),
                    None,
                    f"{fmt_int(c.manami)} animes do MAL no anime-offline-database.",
                ),  # fmt: skip
                (
                    "Com notas do Jikan",
                    fmt_pct(c.jikan_ok / c.mal_ok if c.mal_ok else None),
                    None,
                    f"{fmt_int(c.jikan_ok)} animes.",
                ),  # fmt: skip
                ("Interações Kaggle", fmt_compact(c.kaggle_rows), None, None),
                ("Extrações no histórico", fmt_compact(c.extractions), None, "Bronze é append-only."),
            ]
        )
    runs = q(
        """SELECT command AS comando, started_at AS inicio, finished_at AS fim, status, rows_written AS linhas,
                  date_diff('minute', started_at, coalesce(finished_at, started_at)) AS minutos, notes AS notas
           FROM meta.runs ORDER BY started_at DESC LIMIT 25"""
    )
    if not runs.empty:
        st.subheader("Últimas execuções")
        st.dataframe(runs, hide_index=True, width="stretch")
    http = q("SELECT http_status, count(*) AS n FROM bronze.mal_anime GROUP BY 1 ORDER BY n DESC")
    if not http.empty:
        st.subheader("Respostas da MAL API por status HTTP")
        st.dataframe(http, hide_index=True)
    if table_exists("meta.runs"):
        st.caption(f"Banco: `{DB_PATH}`")
