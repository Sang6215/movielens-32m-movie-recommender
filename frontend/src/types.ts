export interface Genre {
  id: string;
  label: string;
}

export interface Movie {
  movieId: number;
  title: string;
  displayTitle: string;
  year: number | null;
  genres: string[];
  genresVi: string[];
  matchedGenresVi: string[];
  rating: number | null;
  ratingCount: number;
  posterUrl: string;
  backdropUrl: string | null;
  posterPending: boolean;
  overview: string | null;
  overviewLang: string | null;
  titleVi: string | null;
  tmdbUrl: string | null;
  imdbUrl: string | null;
}

export interface MetaResponse {
  genres: Genre[];
  totalMovies: number;
  moviesWithRatings: number;
  ratingCount: number;
  tmdbConfigured: boolean;
}

export interface MoviesResponse {
  items: Movie[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  pendingPosters: number;
}

export interface PosterResponse {
  items: Movie[];
  pendingPosters: number;
}
