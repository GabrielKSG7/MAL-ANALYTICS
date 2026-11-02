"""Gerador de dados **sintéticos** no formato exato das APIs.

Serve para três coisas:
1. Rodar o projeto inteiro (bronze → dbt → recomendador → dashboard) sem credenciais.
2. CI determinístico no GitHub Actions (sem depender de APIs externas).
3. Documentar, por código, o contrato dos payloads que o dbt espera.

Todos os títulos, estúdios, personagens e dubladores são inventados. Os IDs de gênero
seguem a taxonomia pública do MAL. Os números (notas, membros) são simulados a partir
de um modelo latente simples — não representam o MAL real.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from malpipe.warehouse import RunContext, Warehouse, to_json

GENRES = [
    (1, "Action"), (2, "Adventure"), (4, "Comedy"), (8, "Drama"), (10, "Fantasy"),
    (14, "Horror"), (7, "Mystery"), (22, "Romance"), (24, "Sci-Fi"), (36, "Slice of Life"),
    (30, "Sports"), (37, "Supernatural"), (41, "Suspense"), (46, "Award Winning"),
]  # fmt: skip
STUDIOS = [
    (9001, "Studio Aurora"), (9002, "Kumo Animation"), (9003, "Hoshi Works"), (9004, "Pixel Lotus"),
    (9005, "Tsubame Pictures"), (9006, "Neon Koi"), (9007, "Akatsuki Frame"), (9008, "Mori Studio"),
    (9009, "Blue Lantern"), (9010, "Shiro Motion"), (9011, "Inkwave"), (9012, "Hikari Lab"),
]  # fmt: skip
SOURCES = ["manga", "original", "light_novel", "web_manga", "visual_novel", "novel", "game"]
MEDIA = ["tv", "tv", "tv", "tv", "movie", "ova", "ona", "special"]
RATINGS = ["g", "pg", "pg_13", "pg_13", "r", "r+"]
TAGS = [
    "time travel", "isekai", "school", "military", "music", "found family", "revenge",
    "detective", "space", "mecha", "cooking", "tournament", "post-apocalyptic", "idol",
    "psychological", "historical", "magic school", "workplace", "vampires", "survival game",
]  # fmt: skip
SYL = ["ka", "ze", "hi", "ka", "ri", "no", "mo", "ri", "yu", "ki", "sa", "ku", "ra", "ta", "ma",
       "shi", "ro", "ne", "ko", "u", "mi", "so", "ra", "ha", "na", "to", "ki", "ya", "mi", "tsu"]  # fmt: skip
SUFFIX = ["Chronicle", "Overdrive", "Diaries", "Requiem", "Horizon", "Academy", "Saga", "Rhapsody", ""]
SEASONS = ["winter", "spring", "summer", "fall"]
SEASON_MONTH = {"winter": 1, "spring": 4, "summer": 7, "fall": 10}
STATUS_CODE = {"watching": 1, "completed": 2, "on_hold": 3, "dropped": 4, "plan_to_watch": 6}

SAMPLE_USERNAME = "demo_user"


@dataclass
class Anime:
    mal_id: int
    title: str
    genres: list[int]
    studio: tuple[int, str]
    year: int
    season: str
    media_type: str
    episodes: int
    quality: float  # qualidade latente (z-score)
    polarization: float  # 0 = consenso, 1 = divide opiniões
    popularity_w: float
    source: str
    rating: str
    tags: list[str]
    franchise: int
    order_in_franchise: int


def _word(rng: np.random.Generator) -> str:
    n = rng.integers(2, 4)
    return "".join(rng.choice(SYL, n)).capitalize()


def _title(rng: np.random.Generator) -> str:
    base = f"{_word(rng)} no {_word(rng)}" if rng.random() < 0.6 else _word(rng)
    suffix = rng.choice(SUFFIX)
    return f"{base} {suffix}".strip()


def build_catalog(rng: np.random.Generator, n_anime: int) -> list[Anime]:
    catalog: list[Anime] = []
    mal_id = 1000
    franchise = 0
    studio_skill = {s[0]: rng.normal(0, 0.5) for s in STUDIOS}
    while len(catalog) < n_anime:
        franchise += 1
        size = int(rng.choice([1, 1, 1, 2, 2, 3, 4]))
        title = _title(rng)
        genres = sorted(rng.choice([g[0] for g in GENRES[:13]], rng.integers(1, 4), replace=False).tolist())
        if rng.random() < 0.05:
            genres.append(46)
        studio = STUDIOS[rng.integers(len(STUDIOS))]
        year = int(rng.integers(2000, 2025))
        base_q = rng.normal(0, 1) + studio_skill[studio[0]]
        source = str(rng.choice(SOURCES))
        tags = sorted(rng.choice(TAGS, rng.integers(1, 4), replace=False).tolist())
        pol = float(rng.beta(2, 5))
        for k in range(size):
            mal_id += int(rng.integers(1, 40))
            season_title = title if k == 0 else f"{title} {['', '2nd Season', 'Season 3', 'Final Season'][k]}"
            catalog.append(
                Anime(
                    mal_id=mal_id,
                    title=season_title,
                    genres=genres,
                    studio=studio if rng.random() > 0.2 else STUDIOS[rng.integers(len(STUDIOS))],
                    year=min(2025, year + k * int(rng.integers(1, 3))),
                    season=str(rng.choice(SEASONS)),
                    media_type="tv" if k else str(rng.choice(MEDIA)),
                    episodes=int(rng.choice([1, 12, 12, 12, 13, 24, 25, 26, 50])),
                    quality=base_q + k * 0.15 + rng.normal(0, 0.25),  # sequências tendem a ser melhor avaliadas
                    polarization=pol,
                    popularity_w=float(math.exp(rng.normal(0, 1.2) + 0.4 * base_q - 0.3 * k)),
                    source=source,
                    rating=str(rng.choice(RATINGS)),
                    tags=tags,
                    franchise=franchise,
                    order_in_franchise=k,
                )
            )
    return catalog[:n_anime]


def score_distribution(mean_target: float, polarization: float, total_votes: int) -> list[dict]:
    """Distribuição 1–10 com média aproximada e um componente bimodal para títulos polarizados."""
    scores = np.arange(1, 11)
    peak = np.exp(-0.5 * ((scores - mean_target) / 1.1) ** 2)
    extremes = np.where(scores >= 9, 1.0, 0.0) + np.where(scores <= 3, 0.6, 0.0)
    probs = (1 - polarization) * peak / peak.sum() + polarization * extremes / extremes.sum()
    probs = probs / probs.sum()
    votes = np.round(probs * total_votes).astype(int)
    return [
        {"score": int(s), "votes": int(v), "percentage": round(float(p) * 100, 1)}
        for s, v, p in zip(scores, votes, probs, strict=True)
    ]


def mal_payload(a: Anime, catalog_by_franchise: dict[int, list[Anime]], snapshot: int, rng) -> dict:
    mean = float(np.clip(7.0 + 0.75 * a.quality + snapshot * rng.normal(0.01, 0.02), 4.5, 9.3))
    members = int(2000 + 900_000 * a.popularity_w / 6 * (1 + 0.03 * snapshot))
    scoring = int(members * rng.uniform(0.45, 0.65))
    month = SEASON_MONTH[a.season]
    start = datetime(a.year, month, int(rng.integers(1, 28)))
    end = start + timedelta(weeks=max(a.episodes, 1)) if a.media_type in ("tv", "ona") else start
    completed = int(members * 0.60)
    related = []
    for other in catalog_by_franchise[a.franchise]:
        if other.mal_id == a.mal_id:
            continue
        rel = "sequel" if other.order_in_franchise > a.order_in_franchise else "prequel"
        related.append(
            {
                "node": {"id": other.mal_id, "title": other.title},
                "relation_type": rel,
                "relation_type_formatted": rel.capitalize(),
            }
        )
    return {
        "id": a.mal_id,
        "title": a.title,
        "main_picture": {"medium": f"https://example.invalid/{a.mal_id}.jpg"},
        "alternative_titles": {"synonyms": [], "en": a.title.upper(), "ja": ""},
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "synopsis": f"[sintético] Uma história de {', '.join(a.tags)}.",
        "mean": round(mean, 2),
        "rank": None,  # recalculado abaixo
        "popularity": None,
        "num_list_users": members,
        "num_scoring_users": scoring,
        "nsfw": "white",
        "created_at": f"{a.year - 1}-12-01T00:00:00+00:00",
        "updated_at": "2026-10-01T00:00:00+00:00",
        "media_type": a.media_type,
        "status": "finished_airing",
        "genres": [{"id": g, "name": dict(GENRES)[g]} for g in a.genres],
        "num_episodes": a.episodes,
        "start_season": {"year": a.year, "season": a.season},
        "broadcast": {"day_of_the_week": "saturday", "start_time": "23:00"},
        "source": a.source,
        "average_episode_duration": 1440 if a.media_type != "movie" else 6600,
        "rating": a.rating,
        "studios": [{"id": a.studio[0], "name": a.studio[1]}],
        "related_anime": related,
        # A API devolve os contadores de status como STRING — reproduzimos isso de propósito.
        "statistics": {
            "status": {
                "watching": str(int(members * 0.08)),
                "completed": str(completed),
                "on_hold": str(int(members * 0.05)),
                "dropped": str(int(members * (0.03 + 0.05 * a.polarization))),
                "plan_to_watch": str(int(members * 0.21)),
            },
            "num_list_users": members,
        },
    }


def generate(wh: Warehouse, run: RunContext, n_anime: int = 400, n_users: int = 1500, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    catalog = build_catalog(rng, n_anime)
    by_franchise: dict[int, list[Anime]] = {}
    for a in catalog:
        by_franchise.setdefault(a.franchise, []).append(a)

    now = datetime(2026, 10, 25)
    snapshots = [now - timedelta(days=14), now - timedelta(days=7), now]
    counts: dict[str, int] = {}

    # ---- discovery
    rows = [(a.mal_id, "ranking:all", snapshots[0], run.run_id) for a in catalog]
    counts["mal_anime_discovery"] = wh.insert_rows(
        "bronze.mal_anime_discovery", ("mal_id", "discovered_via", "extracted_at", "run_id"), rows
    )

    # ---- detalhes MAL: 3 snapshots semanais (histórico de nota/membros) + alguns 404
    detail_rows = []
    for s_idx, ts in enumerate(snapshots):
        payloads = [mal_payload(a, by_franchise, s_idx, rng) for a in catalog]
        by_mean = sorted(payloads, key=lambda p: -p["mean"])
        by_members = sorted(payloads, key=lambda p: -p["num_list_users"])
        for rank, p in enumerate(by_mean, start=1):
            p["rank"] = rank
        for pop, p in enumerate(by_members, start=1):
            p["popularity"] = pop
        detail_rows += [(p["id"], 200, to_json(p), None, ts, run.run_id) for p in payloads]
    for missing_id in (1, 2, 3):
        detail_rows.append((missing_id, 404, None, '{"error":"not_found"}', snapshots[0], run.run_id))
    counts["mal_anime"] = wh.insert_rows(
        "bronze.mal_anime", ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id"), detail_rows
    )

    latest_mean = {a.mal_id: float(np.clip(7.0 + 0.75 * a.quality, 4.5, 9.3)) for a in catalog}

    # ---- Jikan: estatísticas, recomendações e personagens
    jcols = ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id")
    stats_rows, rec_rows, char_rows = [], [], []
    voice_actors = [(70000 + i, f"{_word(rng)} {_word(rng)}") for i in range(80)]
    char_id = 500000
    for a in catalog:
        members = int(2000 + 900_000 * a.popularity_w / 6)
        dist = score_distribution(latest_mean[a.mal_id], a.polarization, int(members * 0.55))
        stats_rows.append((a.mal_id, 200, to_json({
            "watching": int(members * 0.08), "completed": int(members * 0.62),
            "on_hold": int(members * 0.05), "dropped": int(members * 0.05),
            "plan_to_watch": int(members * 0.20), "total": members, "scores": dist,
        }), None, now, run.run_id))  # fmt: skip

        similar = [b for b in catalog if b.mal_id != a.mal_id and set(b.genres) & set(a.genres)]
        picks = rng.choice(len(similar), min(5, len(similar)), replace=False) if similar else []
        recs = [
            {"entry": {"mal_id": similar[i].mal_id, "title": similar[i].title}, "votes": int(rng.integers(1, 60))}
            for i in picks
        ]
        rec_rows.append((a.mal_id, 200, to_json(recs), None, now, run.run_id))

        chars = []
        for role in ["Main", "Main", "Supporting", "Supporting", "Supporting"]:
            char_id += 1
            va = voice_actors[int(rng.integers(len(voice_actors)))]
            chars.append({
                "character": {"mal_id": char_id, "name": f"{_word(rng)}, {_word(rng)}"},
                "role": role,
                "favorites": int(rng.integers(0, 5000)),
                "voice_actors": [{"person": {"mal_id": va[0], "name": va[1]}, "language": "Japanese"}],
            })  # fmt: skip
        char_rows.append((a.mal_id, 200, to_json(chars), None, now, run.run_id))
    counts["jikan_statistics"] = wh.insert_rows("bronze.jikan_statistics", jcols, stats_rows)
    counts["jikan_recommendations"] = wh.insert_rows("bronze.jikan_recommendations", jcols, rec_rows)
    counts["jikan_characters"] = wh.insert_rows("bronze.jikan_characters", jcols, char_rows)

    # ---- manami (com fontes cruzadas)
    manami_rows = []
    for a in catalog:
        entry = {
            "sources": [
                f"https://myanimelist.net/anime/{a.mal_id}",
                f"https://anilist.co/anime/{a.mal_id + 7}",
                f"https://kitsu.app/anime/{a.mal_id + 3}",
            ],
            "title": a.title,
            "type": a.media_type.upper() if a.media_type != "ona" else "ONA",
            "episodes": a.episodes,
            "status": "FINISHED",
            "animeSeason": {"season": a.season.upper(), "year": a.year},
            "picture": f"https://example.invalid/{a.mal_id}.jpg",
            "thumbnail": f"https://example.invalid/{a.mal_id}t.jpg",
            "duration": {"value": 1440, "unit": "SECONDS"},
            "score": {
                "arithmeticGeometricMean": latest_mean[a.mal_id],
                "arithmeticMean": latest_mean[a.mal_id],
                "median": latest_mean[a.mal_id],
            },  # fmt: skip
            "synonyms": [],
            "studios": [a.studio[1].lower()],
            "producers": [],
            "relatedAnime": [
                f"https://myanimelist.net/anime/{o.mal_id}" for o in by_franchise[a.franchise] if o.mal_id != a.mal_id
            ],  # fmt: skip
            "tags": a.tags + [dict(GENRES)[g].lower() for g in a.genres],
        }
        manami_rows.append((to_json(entry), now.date(), now, run.run_id))
    counts["manami_anime"] = wh.insert_rows(
        "bronze.manami_anime", ("payload", "dataset_date", "extracted_at", "run_id"), manami_rows
    )

    # ---- Kaggle: usuários com gosto latente por gênero → sinal real para o filtro colaborativo
    genre_ids = [g[0] for g in GENRES]
    gidx = {g: i for i, g in enumerate(genre_ids)}
    item_genre = np.zeros((len(catalog), len(genre_ids)))
    for j, a in enumerate(catalog):
        for g in a.genres:
            item_genre[j, gidx[g]] = 1.0
    quality = np.array([a.quality for a in catalog])
    pop = np.array([a.popularity_w for a in catalog])
    pop_p = pop / pop.sum()

    kaggle_rows = []
    for user_id in range(1, n_users + 1):
        taste = rng.normal(0, 1, len(genre_ids))
        affinity = item_genre @ taste / np.maximum(item_genre.sum(axis=1), 1)
        weights = pop_p * np.exp(1.2 * affinity)
        weights /= weights.sum()
        n_items = int(np.clip(rng.lognormal(3.2, 0.6), 5, min(180, len(catalog) // 2)))
        items = rng.choice(len(catalog), n_items, replace=False, p=weights)
        harshness = rng.normal(0, 0.6)
        for j in items:
            latent = 7.0 + 0.8 * quality[j] + 0.9 * affinity[j] - harshness + rng.normal(0, 0.9)
            r = rng.random()
            status = "completed" if r < 0.68 else "watching" if r < 0.78 else "plan_to_watch" if r < 0.9 \
                else "dropped" if r < 0.96 else "on_hold"  # fmt: skip
            if latent < 5.2 and rng.random() < 0.5:
                status = "dropped"
            score = int(np.clip(round(latent), 1, 10)) if status in ("completed", "dropped") \
                and rng.random() < 0.9 else 0  # fmt: skip
            eps = catalog[j].episodes if status == "completed" else int(rng.integers(0, catalog[j].episodes + 1))
            kaggle_rows.append(
                (user_id, catalog[j].mal_id, score, STATUS_CODE[status], eps, "animelist_sample.csv", now, run.run_id)
            )
    counts["kaggle_animelist"] = wh.insert_rows(
        "bronze.kaggle_animelist",
        (
            "user_id",
            "anime_id",
            "score",
            "watching_status",
            "watched_episodes",
            "source_file",
            "loaded_at",
            "run_id",
        ),  # fmt: skip
        kaggle_rows,
    )

    # ---- lista "pessoal" (formato da API /users/{name}/animelist)
    taste = rng.normal(0, 1, len(genre_ids))
    affinity = item_genre @ taste / np.maximum(item_genre.sum(axis=1), 1)
    weights = pop_p * np.exp(1.5 * affinity)
    weights /= weights.sum()
    my_items = rng.choice(len(catalog), min(120, len(catalog) // 2), replace=False, p=weights)
    my_rows = []
    for j in my_items:
        a = catalog[j]
        latent = 7.0 + 0.7 * quality[j] + 1.0 * affinity[j] + rng.normal(0, 0.8)
        status = "completed" if rng.random() < 0.75 else str(rng.choice(["watching", "plan_to_watch", "dropped"]))
        score = int(np.clip(round(latent), 1, 10)) if status in ("completed", "dropped") else 0
        finish = datetime(int(rng.integers(max(a.year, 2012), 2027)), int(rng.integers(1, 13)), 1)
        item = {
            "node": {"id": a.mal_id, "title": a.title},
            "list_status": {
                "status": status,
                "score": score,
                "num_episodes_watched": a.episodes if status == "completed" else 0,
                "is_rewatching": False,
                "num_times_rewatched": 0,
                "updated_at": f"{finish:%Y-%m-%d}T12:00:00+00:00",
                "finish_date": f"{finish:%Y-%m-%d}" if status == "completed" else None,
            },
        }
        my_rows.append((SAMPLE_USERNAME, to_json(item), now, run.run_id))
    counts["mal_user_animelist"] = wh.insert_rows(
        "bronze.mal_user_animelist", ("username", "payload", "extracted_at", "run_id"), my_rows
    )

    counts.update(generate_ecosystem(wh, run, catalog, now, rng))
    run.add(sum(counts.values()))
    run.notes = f"sample seed={seed} n_anime={n_anime} n_users={n_users}"
    return counts


# ============================================================================ ecossistema
STAFF_ROLES = ["Director", "Series Composition", "Original Creator", "Character Design", "Music",
               "Episode Director (ep 3)", "Storyboard (eps 1, 5)", "Animation Director"]  # fmt: skip
OCCUPATIONS = {"Director": "Director", "Series Composition": "Screenwriter", "Original Creator": "Mangaka",
               "Character Design": "Animator", "Music": "Composer"}  # fmt: skip
MANGA_TYPES = ["manga", "manga", "manga", "light_novel", "manhwa", "one_shot", "novel"]
MAGAZINES = ["Weekly Shounen Saikyou", "Young Kumo", "Monthly Hoshi", "Comic Sakura", "Light Novel Bunko"]


def _person(rng, pid: int, name: str, lang: str, occupation: str) -> dict:
    year = int(rng.integers(1955, 2000))
    return {
        "id": pid, "name": {"full": name, "native": None}, "languageV2": lang,
        "gender": str(rng.choice(["Male", "Female"])), "favourites": int(rng.integers(0, 40000)),
        "primaryOccupations": [occupation], "homeTown": str(rng.choice(["Tokyo", "Osaka", "Kanagawa", None])),
        "yearsActive": [year + 22], "dateOfBirth": {"year": year, "month": int(rng.integers(1, 13)), "day": 1},
        "dateOfDeath": {"year": None, "month": None, "day": None}, "image": {"medium": None}, "siteUrl": None,
    }  # fmt: skip


def generate_ecosystem(wh: Warehouse, run: RunContext, catalog: list[Anime], now: datetime, rng) -> dict:
    """AniList (elenco/staff/estúdios), Kitsu (episódios) e MAL mangá — formato real de cada API."""
    counts: dict[str, int] = {}
    seiyuus = [_person(rng, 95000 + i, f"{_word(rng)} {_word(rng)}", "Japanese", "Voice Actor") for i in range(90)]
    dubbers = [_person(rng, 96000 + i, f"{_word(rng)} {_word(rng)}", "English", "Voice Actor") for i in range(30)]
    staff_pool = {
        role: [_person(rng, 97000 + 100 * k + i, f"{_word(rng)} {_word(rng)}", "Japanese", occ) for i in range(25)]
        for k, (role, occ) in enumerate(OCCUPATIONS.items())
    }
    animators = [_person(rng, 98000 + i, f"{_word(rng)} {_word(rng)}", "Japanese", "Animator") for i in range(60)]
    char_id = 800000

    rows_anilist, rows_kitsu = [], []
    for a in catalog:
        if rng.random() < 0.04:  # alguns animes não existem na AniList
            rows_anilist.append((a.mal_id, 404, None, '{"errors":[{"message":"Not Found."}]}', now, run.run_id))
            continue
        characters = []
        for role in ["MAIN", "MAIN", "SUPPORTING", "SUPPORTING", "SUPPORTING", "BACKGROUND"]:
            char_id += 1
            jp = seiyuus[int(rng.integers(len(seiyuus)))]
            vas = [{"roleNotes": None, "dubGroup": None, "voiceActor": jp}]
            if rng.random() < 0.4:
                dub = dubbers[int(rng.integers(len(dubbers)))]
                vas.append({"roleNotes": None, "dubGroup": None, "voiceActor": dub})
            characters.append({
                "role": role,
                "node": {"id": char_id, "name": {"full": f"{_word(rng)} {_word(rng)}", "native": None},
                         "gender": str(rng.choice(["Male", "Female"])), "age": str(int(rng.integers(10, 40))),
                         "favourites": int(rng.integers(0, 20000)),
                         "dateOfBirth": {"year": None, "month": int(rng.integers(1, 13)), "day": 1},
                         "image": {"medium": None}, "siteUrl": None},
                "voiceActorRoles": vas,
            })  # fmt: skip
        staff = [{"role": role, "node": pool[int(rng.integers(len(pool)))]} for role, pool in staff_pool.items()]
        staff += [{"role": str(rng.choice(STAFF_ROLES[5:])), "node": animators[int(rng.integers(len(animators)))]}
                  for _ in range(4)]  # fmt: skip
        media = {
            "id": a.mal_id + 7, "idMal": a.mal_id,
            "title": {"romaji": a.title, "english": a.title.upper(), "native": None},
            "favourites": int(rng.integers(0, 50000)), "averageScore": int(60 + 10 * a.quality),
            "popularity": int(1000 + 100000 * a.popularity_w), "countryOfOrigin": "JP",
            "tags": [{"name": t.title(), "rank": int(rng.integers(50, 100)), "category": "Theme",
                      "isMediaSpoiler": False} for t in a.tags],
            "studios": {"edges": [{"isMain": True, "node": {"id": a.studio[0] - 8000, "name": a.studio[1],
                                    "isAnimationStudio": True, "favourites": 1000, "siteUrl": None}}]},
            "characters": characters, "staff": staff, "truncated": False,
        }  # fmt: skip
        rows_anilist.append((a.mal_id, 200, to_json(media), None, now, run.run_id))

        if a.media_type in ("tv", "ona", "ova", "special"):
            start = datetime(a.year, SEASON_MONTH[a.season], 5)
            eps = [{
                "kitsu_episode_id": str(a.mal_id * 1000 + n), "number": n, "seasonNumber": 1, "relativeNumber": n,
                "canonicalTitle": f"Episódio {n}: {_word(rng)}", "titles": {"en_jp": f"Episode {n}"},
                "airdate": (start + timedelta(weeks=n - 1)).date().isoformat() if rng.random() > 0.05 else None,
                "length": 24 if a.media_type != "special" else 12, "synopsis": None,
            } for n in range(1, a.episodes + 1)]  # fmt: skip
            rows_kitsu.append((a.mal_id, a.mal_id + 3, 200, to_json(eps), None, now, run.run_id))

    counts["anilist_media"] = wh.insert_rows(
        "bronze.anilist_media", ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id"), rows_anilist
    )
    counts["kitsu_episodes"] = wh.insert_rows(
        "bronze.kitsu_episodes",
        ("mal_id", "kitsu_id", "http_status", "payload", "error", "extracted_at", "run_id"),
        rows_kitsu,
    )

    # ---- mangás: metade das franquias tem obra original em mangá/LN ligada ao anime
    disc, details = [], []
    manga_id = 2000
    authors = [(30000 + i, _word(rng), _word(rng)) for i in range(70)]
    first_of_franchise = {}
    for a in catalog:
        first_of_franchise.setdefault(a.franchise, a)
    adapted = list(first_of_franchise.values())
    for i in range(int(len(adapted) * 1.6)):
        manga_id += int(rng.integers(1, 30))
        source = adapted[i] if i < len(adapted) and adapted[i].source in ("manga", "light_novel", "web_manga") else None
        mtype = "light_novel" if source and source.source == "light_novel" else str(rng.choice(MANGA_TYPES))
        year = (source.year - int(rng.integers(1, 6))) if source else int(rng.integers(1985, 2025))
        q = (source.quality + rng.normal(0.2, 0.4)) if source else rng.normal(-0.2, 1)
        author = authors[int(rng.integers(len(authors)))]
        payload = {
            "id": manga_id, "title": source.title.split(" 2nd")[0] if source else _title(rng),
            "main_picture": {"medium": f"https://example.invalid/m{manga_id}.jpg"},
            "alternative_titles": {"synonyms": [], "en": "", "ja": ""},
            "start_date": f"{year}-0{int(rng.integers(1, 9))}-01", "end_date": None,
            "synopsis": "[sintético]", "mean": round(float(np.clip(7.2 + 0.7 * q, 4.5, 9.4)), 2),
            "rank": None, "popularity": None, "num_list_users": int(500 + 300000 * abs(rng.normal(0, 1))),
            "num_scoring_users": int(200 + 100000 * abs(rng.normal(0, 1))), "nsfw": "white",
            "genres": [{"id": g, "name": dict(GENRES)[g]} for g in (source.genres if source else [1, 8])],
            "media_type": mtype, "status": str(rng.choice(["finished", "currently_publishing", "on_hiatus"])),
            "num_volumes": int(rng.integers(1, 40)), "num_chapters": int(rng.integers(5, 400)),
            "authors": [{"node": {"id": author[0], "first_name": author[1], "last_name": author[2]},
                         "role": "Story & Art"}],
            "serialization": [{"node": {"id": 500 + i % 5, "name": MAGAZINES[i % 5]}}],
            "related_anime": ([{"node": {"id": source.mal_id, "title": source.title}, "relation_type": "adaptation"}]
                              if source else []),
            "related_manga": [],
        }  # fmt: skip
        disc.append((manga_id, "ranking:all", now, run.run_id))
        details.append((manga_id, 200, to_json(payload), None, now, run.run_id))
    counts["mal_manga_discovery"] = wh.insert_rows(
        "bronze.mal_manga_discovery", ("mal_id", "discovered_via", "extracted_at", "run_id"), disc
    )
    counts["mal_manga"] = wh.insert_rows(
        "bronze.mal_manga", ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id"), details
    )
    return counts
