"""Infra do dashboard: acesso ao DuckDB, filtros globais, formatação e estilo dos gráficos."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:  # mesma regra do pipeline: DUCKDB_PATH do .env (caminho relativo = raiz do projeto)
    from malpipe.config import get_settings

    DB_PATH = get_settings().duckdb_path
    DEFAULT_USER = get_settings().mal_username
except ImportError:  # pragma: no cover
    DB_PATH = Path(os.getenv("DUCKDB_PATH", Path(__file__).resolve().parents[1] / "data" / "mal.duckdb"))
    DEFAULT_USER = os.getenv("MAL_USERNAME")

# ----------------------------------------------------------------------------- paleta
# Categórica em ordem fixa (validada para daltonismo em pares adjacentes); a cor segue a
# entidade, nunca a posição. Azul sozinho = magnitude. Azul ↔ vermelho = diferença com sinal.
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
MAGENTA, GREEN, VIOLET, RED = "#e87ba4", "#008300", "#6250d6", "#e34948"
GRAY = "#8a8985"
SOURCE_COLORS = {"Original": BLUE, "Mangá": ORANGE, "Light novel": AQUA, "Outras": GRAY}
STATUS_COLORS = {
    "completed": BLUE,
    "watching": AQUA,
    "on_hold": YELLOW,
    "dropped": RED,
    "plan_to_watch": GRAY,
}
STATUS_LABELS = {
    "completed": "Completo",
    "watching": "Assistindo",
    "on_hold": "Pausado",
    "dropped": "Abandonado",
    "plan_to_watch": "Plan to watch",
}
MEDIA_LABELS = {
    "tv": "TV",
    "movie": "Filme",
    "ona": "ONA (web)",
    "ova": "OVA",
    "special": "Especial",
    "tv_special": "Especial de TV",
    "music": "Clipe",
    "pv": "PV",
    "cm": "Comercial",
    "unknown": "Desconhecido",
}


# ----------------------------------------------------------------------------- dados
def db_available() -> bool:
    return Path(DB_PATH).exists()


@st.cache_data(ttl=300, show_spinner=False)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Consulta somente leitura com conexão curta.

    Abrir e fechar a cada consulta evita que o dashboard segure o arquivo — assim dá para
    rodar `build`/ingestão com o painel aberto (o DuckDB aceita um escritor por vez).
    """
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    except duckdb.Error:
        return pd.DataFrame()
    try:
        return con.execute(sql, [list(p) if isinstance(p, tuple) else p for p in params]).df()
    except duckdb.Error:
        return pd.DataFrame()
    finally:
        con.close()


def table_exists(name: str) -> bool:
    schema, table = name.split(".")
    df = q(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
        (schema, table),
    )
    return not df.empty


# ----------------------------------------------------------------------------- filtros
@dataclass(frozen=True)
class Filters:
    years: tuple[int, int]
    media: tuple[str, ...]
    genres: tuple[str, ...]
    min_members: int

    def where(self, alias: str = "a") -> tuple[str, tuple]:
        """Cláusula WHERE (sem a palavra WHERE) + parâmetros, para consultas em core.dim_anime."""
        clauses = [f"{alias}.season_year BETWEEN ? AND ?", f"coalesce({alias}.num_list_users, 0) >= ?"]
        params: list = [self.years[0], self.years[1], self.min_members]
        if self.media:
            clauses.append(f"{alias}.media_type IN ({', '.join('?' for _ in self.media)})")
            params += list(self.media)
        if self.genres:
            clauses.append(f"list_has_any({alias}.genres, ?)")
            params.append(tuple(self.genres))
        return " AND ".join(clauses), tuple(params)

    def describe(self) -> str:
        parts = [f"{self.years[0]}–{self.years[1]}"]
        parts.append(", ".join(MEDIA_LABELS.get(m, m) for m in self.media) if self.media else "todos os formatos")
        if self.genres:
            parts.append(" + ".join(self.genres))
        if self.min_members:
            parts.append(f"≥ {fmt_int(self.min_members)} membros")
        return " · ".join(parts)


def sidebar_filters() -> Filters:
    bounds = q(
        "SELECT min(season_year)::INT AS lo, max(season_year)::INT AS hi FROM core.dim_anime "
        "WHERE season_year BETWEEN 1910 AND 2035"
    )
    lo, hi = (1960, 2026) if bounds.empty or pd.isna(bounds.lo[0]) else (int(bounds.lo[0]), int(bounds.hi[0]))
    genres = q("SELECT genre_name FROM core.dim_genre ORDER BY num_anime DESC")
    media = q("SELECT media_type, count(*) n FROM core.dim_anime GROUP BY 1 ORDER BY n DESC")

    st.sidebar.header("Filtros")
    st.sidebar.caption("Valem para as abas Visão geral, Tendências e Explorar.")
    years = st.sidebar.slider("Ano de estreia", lo, hi, (max(lo, 1990), hi))
    media_opts = media.media_type.dropna().tolist() if not media.empty else []
    default_media = [m for m in ("tv", "movie", "ona", "ova") if m in media_opts]
    media_sel = st.sidebar.multiselect(
        "Formato", media_opts, default=default_media, format_func=lambda m: MEDIA_LABELS.get(m, m)
    )
    genre_sel = st.sidebar.multiselect(
        "Gêneros (qualquer um)", genres.genre_name.tolist() if not genres.empty else [], placeholder="Todos"
    )
    min_members = st.sidebar.select_slider(
        "Mínimo de membros",
        options=[0, 1_000, 10_000, 50_000, 100_000, 500_000, 1_000_000],
        value=1_000,
        format_func=fmt_int,
    )
    return Filters(tuple(years), tuple(media_sel), tuple(genre_sel), int(min_members))


# ----------------------------------------------------------------------------- formatação pt-BR
def fmt_int(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{int(round(v)):,}".replace(",", ".")


def fmt_dec(v, digits: int = 2) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v, digits: int = 0) -> str:
    if v is None or pd.isna(v):
        return "—"
    return fmt_dec(v * 100, digits) + "%"


def fmt_compact(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    for div, suf in ((1e9, " bi"), (1e6, " mi"), (1e3, " mil")):
        if abs(v) >= div:
            return fmt_dec(v / div, 1) + suf
    return fmt_int(v)


# ----------------------------------------------------------------------------- gráficos
def style(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=86 if legend else 56, b=8),
        hoverlabel=dict(namelength=-1),
        showlegend=legend,
        # título no topo do container e legenda logo acima da área do gráfico: não se sobrepõem
        title=dict(font=dict(size=15), y=0.98, yref="container", yanchor="top", x=0.01),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0, title_text=""),
        separators=",.",
        bargap=0.15,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridwidth=1, zeroline=False)
    return fig


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", theme="streamlit", config={"displaylogo": False})


def poster_columns(extra: dict | None = None) -> dict:
    """Configuração de colunas com pôster, link e barra de nota para st.dataframe."""
    cfg = {
        "picture_url": st.column_config.ImageColumn("", width="small"),
        "mal_url": st.column_config.LinkColumn("MAL", display_text="abrir"),
        "title": st.column_config.TextColumn("Título", width="large"),
        "mean_score": st.column_config.ProgressColumn("Nota", min_value=1, max_value=10, format="%.2f"),
        "weighted_score": st.column_config.NumberColumn("Nota bayesiana", format="%.2f"),
        "num_list_users": st.column_config.NumberColumn("Membros", format="localized"),
        "season_year": st.column_config.NumberColumn("Ano", format="%d"),
        "main_studio_name": "Estúdio",
        "genres_label": "Gêneros",
        "media_type": "Formato",
    }
    cfg.update(extra or {})
    return cfg


def empty_state(msg: str) -> None:
    st.info(msg, icon="ℹ️")
