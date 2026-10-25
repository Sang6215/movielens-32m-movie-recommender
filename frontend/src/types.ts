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
  predictionScore?: number | null;
  personalRank?: number;
  historyRating?: number;
  recommendationReason?: string;
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

export interface ALSMetaResponse {
  users: number;
  candidateMovies: number;
  minRatingCount: number;
  topK: number;
  exampleUserIds: number[];
  selectedParams: { rank: number; regParam: number; maxIter: number };
  testRatingMetrics: { rmse: number; mae: number; coverage: number };
}

export interface PersonalResponse extends PosterResponse {
  userId: number;
  knownUser: boolean;
  strategy: "als" | "weighted_score_fallback";
  history: Movie[];
  historyCount: number;
  message: string;
}

export interface DemoRecommendationsResponse extends PosterResponse {
  watchedCount: number;
  genres: Array<{ id: string; label: string; count: number }>;
  strategy: "genre_history" | "community_fallback";
  history: Movie[];
  message: string;
}

export interface ChartPoint { label: string; value: number }

export interface AnalyticsResponse {
  schemaVersion: number;
  snapshot: { trainingDate: string; benchmarkDate: string; hdfsDate: string; kind: string };
  dataset: {
    ratings: number; users: number; movies: number; ratedMovies: number; tags: number;
    firstRating: string; lastRating: string; sparsity: number;
    ratingsDistribution: ChartPoint[]; genres: ChartPoint[]; ratingsByYear: ChartPoint[];
  };
  performance: {
    storage: Array<{ dataset: string; csv_size_mb: number; parquet_size_mb: number; space_saving_pct: number }>;
    query: { query: string; master: string; runs: number; csv_times_sec: number[]; parquet_times_sec: number[]; csv_median_sec: number; parquet_median_sec: number; parquet_speedup_x: number };
    threads: Array<{ master: string; threads: number; train_rows: number; valid_rows: number; total_sec: number; speedup_vs_1_thread: number }>;
  };
  model: {
    trainRows: number; validationRows: number; testRows: number; fitRows: number;
    params: { rank: number; regParam: number; maxIter: number };
    test: { rows: number; rmse: number; mae: number; coverage: number };
    tuning: Array<{ iterations: number; rmse: number; mae: number }>;
    rankingUsers: number;
    ranking: Array<{ label: string; candidates: number; precision: number; recall: number; ndcg: number }>;
  };
  hdfs: {
    date: string; dataNodes: number; sparkMaster: string; sparkVersion: string; hadoopVersion: string;
    modelRetrained: boolean; rawRows: number; readbackRows: number; invalidRows: number; duplicates: number; success: boolean;
  };
  sources: Array<{ label: string; path: string }>;
}
