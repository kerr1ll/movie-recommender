"use strict";

const storageKey = "kino-dlya-tebya-ratings-v1";
const movieCatalog = [...movies].sort((left, right) =>
  normalizeTitle(left.title).localeCompare(normalizeTitle(right.title), "ru"));
const byId = id => document.getElementById(id);
const search = byId("search");
const movieList = byId("movie-list");
const pickList = byId("pick-list");
const catalogTab = byId("catalog-tab");
const picksTab = byId("picks-tab");
const storageStatus = byId("storage-status");

let ratings = {};
try {
  ratings = readRatings(window.localStorage, storageKey);
} catch {
  storageStatus.hidden = false;
  storageStatus.textContent = "Не удалось загрузить сохранённые оценки.";
}

function makeElement(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function movieCard(movie) {
  const card = makeElement("li", "", "card");
  const metadata = [movie.year, ...movie.genres].join(" · ");
  card.append(makeElement("h2", movie.title), makeElement("p", metadata, "meta"));
  return card;
}

function rateMovie(movie, rating, group) {
  ratings[movie.id] = rating;
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(ratings));
    storageStatus.hidden = true;
  } catch {
    storageStatus.textContent = "Оценка действует до закрытия страницы. Браузер не сохранил её.";
    storageStatus.hidden = false;
  }
  for (const button of group.children) {
    button.setAttribute("aria-pressed", String(Number(button.textContent) === rating));
  }
  byId("rating-status").textContent = `«${movie.title}» — оценка ${rating} из 5.`;
  renderPicks();
}

function renderCatalog() {
  const matches = searchMovies(movieCatalog, search.value);
  byId("catalog-status").textContent = matches.length
    ? `Фильмов в списке: ${matches.length}. Оценки от 1 до 5.`
    : "По этому запросу фильмов нет.";
  movieList.replaceChildren(...matches.map(movie => {
    const card = movieCard(movie);
    const group = makeElement("div", "", "rating");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", `Оценка фильма «${movie.title}»`);
    for (let rating = 1; rating <= 5; rating += 1) {
      const button = makeElement("button", String(rating));
      button.type = "button";
      button.setAttribute("aria-label", `Оценка ${rating} из 5`);
      button.setAttribute("aria-pressed", String(ratings[movie.id] === rating));
      button.addEventListener("click", () => rateMovie(movie, rating, group));
      group.append(button);
    }
    card.append(group);
    return card;
  }));
}

function renderPicks() {
  const picks = recommendMovies(movies, ratings);
  const count = byId("pick-count");
  count.textContent = picks.length;
  count.hidden = picks.length === 0;

  const rated = movies.filter(movie => ratings[movie.id]).map(movie => ratings[movie.id]);
  const status = byId("picks-status");
  if (picks.length) {
    status.textContent = `Оценено фильмов: ${rated.length}.`;
  } else if (rated.length === movies.length) {
    status.textContent = "Ты оценил все фильмы в каталоге.";
  } else if (rated.some(rating => rating > 3)) {
    status.textContent = "Подходящих фильмов пока нет. Попробуй оценить ещё несколько.";
  } else {
    status.textContent = "Поставь 4 или 5 хотя бы одному понравившемуся фильму.";
  }

  byId("back-to-catalog").hidden = picks.length > 0 || rated.length === movies.length;
  pickList.replaceChildren(...picks.map(({ movie, reason }) => {
    const card = movieCard(movie);
    card.append(makeElement(
      "p", `Похож на «${reason.movie.title}». Общие признаки — ${reason.shared.join(", ")}.`, "reason",
    ));
    return card;
  }));
}

function showSection(showPicks) {
  byId("catalog").hidden = showPicks;
  byId("picks").hidden = !showPicks;
  catalogTab.setAttribute("aria-pressed", String(!showPicks));
  picksTab.setAttribute("aria-pressed", String(showPicks));
}

search.addEventListener("input", renderCatalog);
catalogTab.addEventListener("click", () => showSection(false));
picksTab.addEventListener("click", () => showSection(true));
byId("back-to-catalog").addEventListener("click", () => {
  showSection(false);
  catalogTab.focus();
});

renderCatalog();
renderPicks();
