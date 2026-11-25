"""Окно персональной рекомендательной системы."""

import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from recommender import RatingsStore, load_movies, normalize, recommend, search_movies


PROJECT_DIR = Path(__file__).resolve().parent


class MovieApp:
    def __init__(self, root: tk.Tk, data_dir: Path):
        self.root = root
        self.movies = sorted(
            load_movies(data_dir / "movies.csv"), key=lambda movie: normalize(movie.title)
        )
        self.store = RatingsStore(data_dir / "ratings.sqlite3")
        self.ratings = self.store.load()
        self.recommendations = {}

        root.title("Персональные рекомендации фильмов")
        root.geometry("1120x620")
        root.minsize(900, 480)

        content = ttk.Frame(root, padding=16)
        content.pack(fill="both", expand=True)
        content.columnconfigure((0, 1), weight=1, uniform="panels")
        content.rowconfigure(0, weight=1)

        catalog = ttk.LabelFrame(content, text="Каталог фильмов", padding=12)
        catalog.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.query = tk.StringVar()
        ttk.Label(catalog, text="Поиск по названию").pack(anchor="w")
        search = ttk.Entry(catalog, textvariable=self.query)
        search.pack(fill="x", pady=(4, 8))
        search.focus_set()

        self.catalog = self.make_table(catalog, "Оценка")
        self.catalog.bind("<<TreeviewSelect>>", self.update_rating_buttons)
        rating_row = ttk.Frame(catalog)
        rating_row.pack(fill="x", pady=(12, 4))
        ttk.Label(rating_row, text="Оценить фильм").pack(side="left", padx=(0, 8))
        self.rating_buttons = []
        for value in range(1, 6):
            button = ttk.Button(
                rating_row, text=str(value), width=3,
                command=lambda rating=value: self.rate_movie(rating),
            )
            button.pack(side="left", padx=2)
            self.rating_buttons.append(button)
        self.catalog_status = ttk.Label(catalog)
        self.catalog_status.pack(anchor="w")

        picks = ttk.LabelFrame(content, text="Рекомендации", padding=12)
        picks.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.picks_status = ttk.Label(picks)
        self.picks_status.pack(anchor="w", pady=(0, 8))
        self.picks = self.make_table(picks, "Жанры")
        self.picks.bind("<<TreeviewSelect>>", self.show_reason)
        self.reason = ttk.Label(picks, wraplength=400, justify="left", padding=(0, 8))
        self.reason.pack(fill="x")
        picks.bind("<Configure>", lambda event: self.reason.configure(
            wraplength=max(100, event.width - 30)
        ))

        self.query.trace_add("write", self.refresh_catalog)
        self.refresh_catalog()
        self.refresh_recommendations()

    @staticmethod
    def make_table(parent, last_heading: str) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        columns = ("title", "year", "detail")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("title", text="Фильм")
        tree.heading("year", text="Год")
        tree.heading("detail", text=last_heading)
        tree.column("title", width=230, minwidth=110)
        tree.column("year", width=55, minwidth=55, stretch=False, anchor="center")
        if last_heading == "Оценка":
            tree.column("detail", width=62, minwidth=62, stretch=False, anchor="center")
        else:
            tree.column("detail", width=145, minwidth=90)
        vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        return tree

    def refresh_catalog(self, *_):
        selected = self.catalog.selection()
        self.catalog.delete(*self.catalog.get_children())
        matches = search_movies(self.movies, self.query.get())
        for movie in matches:
            self.catalog.insert(
                "", "end", iid=str(movie.id),
                values=(movie.title, movie.year, self.ratings.get(movie.id, "—")),
            )
        if selected and self.catalog.exists(selected[0]):
            self.catalog.selection_set(selected[0])
            self.catalog.see(selected[0])
        self.catalog_status.configure(text=f"Найдено фильмов: {len(matches)}")
        self.update_rating_buttons()

    def update_rating_buttons(self, _event=None):
        state = "!disabled" if self.catalog.selection() else "disabled"
        for button in self.rating_buttons:
            button.state([state])

    def rate_movie(self, rating: int):
        selected = self.catalog.selection()
        if not selected:
            return
        try:
            self.store.save(int(selected[0]), rating)
            self.ratings = self.store.load()
        except sqlite3.Error as error:
            messagebox.showerror("Ошибка сохранения", str(error), parent=self.root)
            return
        self.refresh_catalog()
        self.refresh_recommendations()

    def refresh_recommendations(self):
        self.picks.delete(*self.picks.get_children())
        recommendations = recommend(self.movies, self.ratings)
        self.recommendations = {str(item.movie.id): item for item in recommendations}
        for item in recommendations:
            movie = item.movie
            self.picks.insert(
                "", "end", iid=str(movie.id),
                values=(movie.title, movie.year, ", ".join(sorted(movie.genres))),
            )

        ratings = [self.ratings[movie.id] for movie in self.movies if movie.id in self.ratings]
        self.picks_status.configure(text=f"Оценено фильмов: {len(ratings)}")
        if recommendations:
            first = str(recommendations[0].movie.id)
            self.picks.selection_set(first)
            self.picks.focus(first)
            self.show_reason()
        elif len(ratings) == len(self.movies):
            self.reason.configure(text="Ты оценил все фильмы в каталоге.")
        elif any(rating > 3 for rating in ratings):
            self.reason.configure(text="Подходящих фильмов пока нет. Оцени ещё несколько.")
        else:
            self.reason.configure(text="Поставь 4 или 5 хотя бы одному понравившемуся фильму.")

    def show_reason(self, _event=None):
        selected = self.picks.selection()
        if selected:
            item = self.recommendations[selected[0]]
            features = ", ".join(item.shared_features)
            self.reason.configure(
                text=f"Похож на фильм «{item.similar_to.title}». Общие жанры и темы — {features}."
            )


def main():
    root = tk.Tk()
    try:
        MovieApp(root, PROJECT_DIR)
    except (OSError, ValueError, KeyError, sqlite3.Error) as error:
        messagebox.showerror("Не удалось открыть проект", str(error), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
