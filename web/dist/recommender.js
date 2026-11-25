"use strict";

function normalizeTitle(text) {
  return text.toLowerCase().replaceAll("ё", "е").replace(/[‑–—]/g, "-")
    .replaceAll(",", "").trim().replace(/\s+/g, " ");
}

function searchMovies(movies, query) {
  const needle = normalizeTitle(query);
  return movies.filter(movie => normalizeTitle(movie.title).includes(needle)
    || normalizeTitle(movie.original_title).includes(needle));
}

function sharedFeatures(first, second) {
  return [
    ...first.genres.filter(genre => second.genres.includes(genre)),
    ...first.tags.filter(tag => second.tags.includes(tag)),
  ];
}

function recommendMovies(movies, ratings, limit = 10) {
  const rated = movies.filter(movie => ratings[movie.id] && ratings[movie.id] !== 3)
    .map(movie => ({ movie, weight: ratings[movie.id] - 3 }));
  const weightTotal = rated.reduce((total, item) => total + Math.abs(item.weight), 0);
  if (!weightTotal || limit <= 0) return [];

  const results = [];
  for (const movie of movies) {
    if (ratings[movie.id]) continue;
    const size = movie.genres.length + movie.tags.length;
    let total = 0;
    let best = 0;
    let reason;
    for (const item of rated) {
      const shared = sharedFeatures(movie, item.movie);
      if (!shared.length) continue;
      const otherSize = item.movie.genres.length + item.movie.tags.length;
      const similarity = shared.length / Math.sqrt(size * otherSize);
      const contribution = item.weight * similarity;
      total += contribution;
      if (contribution > best) {
        best = contribution;
        reason = { movie: item.movie, shared: [...new Set(shared)].sort() };
      }
    }
    if (total > 0) results.push({ movie, score: total / weightTotal, reason });
  }
  results.sort((first, second) => {
    const scoreOrder = second.score - first.score;
    const left = normalizeTitle(first.movie.title);
    const right = normalizeTitle(second.movie.title);
    return scoreOrder || (left > right) - (left < right) || first.movie.id - second.movie.id;
  });
  return results.slice(0, limit);
}

function readRatings(storage, key) {
  const stored = JSON.parse(storage.getItem(key) ?? "{}");
  return Object.fromEntries(Object.entries(stored ?? {}).filter(([id, rating]) =>
    /^\d+$/.test(id) && Number.isInteger(rating) && rating >= 1 && rating <= 5));
}
