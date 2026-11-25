"""Каталог, история оценок и контентная фильтрация."""

import csv
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from math import sqrt
from pathlib import Path


TITLE_TRANSLATION = str.maketrans({"ё": "е", "‑": "-", "–": "-", "—": "-", ",": None})


@dataclass(frozen=True)
class Movie:
    id: int
    title: str
    original_title: str
    year: int
    genres: frozenset[str]
    tags: frozenset[str]


@dataclass(frozen=True)
class Recommendation:
    movie: Movie
    score: float
    similar_to: Movie
    shared_features: tuple[str, ...]


def load_movies(path: Path) -> list[Movie]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        movies = [
            Movie(
                id=int(row["id"]),
                title=row["title"],
                original_title=row["original_title"],
                year=int(row["year"]),
                genres=frozenset(row["genres"].split("|")) - {""},
                tags=frozenset(row["tags"].split("|")) - {""},
            )
            for row in csv.DictReader(file)
        ]
    if not movies or len({movie.id for movie in movies}) != len(movies):
        raise ValueError("Каталог пуст или содержит повторяющиеся идентификаторы.")
    return movies


def normalize(text: str) -> str:
    return " ".join(text.casefold().translate(TITLE_TRANSLATION).split())


def search_movies(movies: list[Movie], query: str) -> list[Movie]:
    query = normalize(query.strip())
    return [
        movie
        for movie in movies
        if query in normalize(movie.title) or query in normalize(movie.original_title)
    ]


class RatingsStore:
    def __init__(self, path: Path):
        self.path = path
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ratings (
                    movie_id INTEGER PRIMARY KEY,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5)
                )
                """
            )

    def load(self) -> dict[int, int]:
        with closing(sqlite3.connect(self.path)) as connection:
            return dict(connection.execute("SELECT movie_id, rating FROM ratings"))

    def save(self, movie_id: int, rating: int) -> None:
        if type(rating) is not int or not 1 <= rating <= 5:
            raise ValueError("Оценка должна быть целым числом от 1 до 5.")
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                """
                INSERT INTO ratings (movie_id, rating) VALUES (?, ?)
                ON CONFLICT(movie_id) DO UPDATE SET rating = excluded.rating
                """,
                (movie_id, rating),
            )


def similarity(first: Movie, second: Movie) -> float:
    """Косинусное сходство. Жанры и темы образуют разные признаки."""
    common = len(first.genres & second.genres) + len(first.tags & second.tags)
    if common == 0:
        return 0.0
    first_size = len(first.genres) + len(first.tags)
    second_size = len(second.genres) + len(second.tags)
    return common / sqrt(first_size * second_size)


def recommend(
    movies: list[Movie], ratings: dict[int, int], limit: int = 10
) -> list[Recommendation]:
    rated = [
        (movie, ratings[movie.id] - 3)
        for movie in movies
        if movie.id in ratings and ratings[movie.id] != 3
    ]
    total_weight = sum(abs(weight) for _, weight in rated)
    if total_weight == 0 or limit <= 0:
        return []

    results = []
    for movie in movies:
        if movie.id in ratings:
            continue

        contributions = [
            (weight * similarity(movie, watched), watched) for watched, weight in rated
        ]
        score = sum(value for value, _ in contributions) / total_weight
        if score <= 0:
            continue

        _, closest = max(contributions, key=lambda pair: pair[0])
        features = (movie.genres & closest.genres) | (movie.tags & closest.tags)
        results.append(Recommendation(movie, score, closest, tuple(sorted(features))))

    results.sort(key=lambda item: (-item.score, normalize(item.movie.title), item.movie.id))
    return results[:limit]
