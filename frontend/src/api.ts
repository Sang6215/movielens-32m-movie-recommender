import type { ALSMetaResponse, MetaResponse, MoviesResponse, PersonalResponse, PosterResponse } from "./types";

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    const error = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new Error(typeof error?.detail === "string" ? error.detail : `Không thể tải dữ liệu phim (${response.status}).`);
  }
  return (await response.json()) as T;
}

export function getMeta(signal?: AbortSignal) {
  return getJson<MetaResponse>("/api/meta", signal);
}

export function getFeatured(signal?: AbortSignal) {
  return getJson<PosterResponse>("/api/featured", signal);
}

export function getMovies(genres: string[], search: string, page: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(page) });
  genres.forEach((genre) => params.append("genres", genre));
  if (search) params.set("search", search);
  return getJson<MoviesResponse>(`/api/movies?${params}`, signal);
}

export function getPosters(movieIds: number[], signal?: AbortSignal) {
  const params = new URLSearchParams();
  movieIds.forEach((movieId) => params.append("movie_ids", String(movieId)));
  return getJson<PosterResponse>(`/api/posters?${params}`, signal);
}

export function getALSMeta(signal?: AbortSignal) {
  return getJson<ALSMetaResponse>("/api/als/meta", signal);
}

export function getPersonalRecommendations(userId: number, signal?: AbortSignal) {
  return getJson<PersonalResponse>(`/api/als/recommendations?user_id=${userId}`, signal);
}
