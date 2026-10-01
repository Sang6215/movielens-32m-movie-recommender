import { useCallback, useEffect, useId, useState, type FormEvent } from "react";
import { getFeatured, getMeta, getMovies, getPosters } from "./api";
import PersonalRecommendations from "./PersonalRecommendations";
import type { MetaResponse, Movie, MoviesResponse } from "./types";

const formatNumber = new Intl.NumberFormat("vi-VN");
const PLACEHOLDER = "/media/poster-placeholder.svg";

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="10.8" cy="10.8" r="6.8" />
      <path d="m16 16 5 5" />
    </svg>
  );
}

function ArrowIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>;
}

function FilmMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span className="brand-frame" />
      <span className="brand-play" />
    </span>
  );
}

function ratingText(rating: number | null) {
  return rating === null ? "Chưa có đánh giá" : `${rating.toFixed(1).replace(".", ",")}/5`;
}

function mergeMovies(current: Movie[], updated: Movie[]): Movie[] {
  const byId = new Map(updated.map((movie) => [movie.movieId, movie]));
  return current.map((movie) => ({ ...movie, ...byId.get(movie.movieId) }));
}

function scrollToResults() {
  document.getElementById("discover")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function Pagination({ page, totalPages, onPageChange }: { page: number; totalPages: number; onPageChange: (page: number) => void }) {
  const pageInputId = useId();
  const [draft, setDraft] = useState(String(page));
  useEffect(() => setDraft(String(page)), [page]);
  if (totalPages <= 1) return null;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = Number(draft);
    if (Number.isInteger(next) && next >= 1 && next <= totalPages) {
      onPageChange(next);
    } else {
      setDraft(String(page));
    }
  }

  return (
    <nav className="pagination" aria-label="Phân trang kết quả">
      <button className="page-arrow" type="button" aria-label="Trang trước" disabled={page <= 1} onClick={() => onPageChange(page - 1)}><ArrowIcon /></button>
      <form onSubmit={submit} className="page-form">
        <label htmlFor={pageInputId}>Trang</label>
        <input id={pageInputId} type="number" min="1" max={totalPages} value={draft} onChange={(event) => setDraft(event.target.value)} aria-label="Số trang kết quả" />
        <span>/ {formatNumber.format(totalPages)}</span>
      </form>
      <button className="page-arrow" type="button" aria-label="Trang sau" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}><ArrowIcon /></button>
    </nav>
  );
}

function MovieCard({ movie, onOpen }: { movie: Movie; onOpen: (movie: Movie) => void }) {
  return (
    <button type="button" className="movie-card" onClick={() => onOpen(movie)} aria-label={`Xem chi tiết ${movie.displayTitle}`}>
      <div className="movie-poster-wrap">
        {movie.personalRank && <span className="personal-rank">#{movie.personalRank}</span>}
        <img src={movie.posterUrl} alt={`Poster phim ${movie.displayTitle}`} loading="lazy" onError={(event) => { event.currentTarget.src = PLACEHOLDER; }} />
      </div>
      <div className="movie-card-body">
        <div className="card-rating"><span className="star">★</span><strong>{ratingText(movie.rating)}</strong><span className="rating-source">MovieLens</span></div>
        {movie.predictionScore !== undefined && movie.predictionScore !== null && <p className="als-score">Điểm ALS <strong>{movie.predictionScore.toFixed(2).replace(".", ",")}</strong></p>}
        <h3>{movie.displayTitle}</h3>
        <p className="card-genres">{movie.genresVi.slice(0, 3).join(" · ") || "Chưa phân loại"}</p>
        <span className="card-detail">Chi tiết phim <ArrowIcon /></span>
      </div>
    </button>
  );
}

function MovieModal({ movie, onClose }: { movie: Movie; onClose: () => void }) {
  useEffect(() => {
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => { document.body.style.overflow = oldOverflow; window.removeEventListener("keydown", onKeyDown); };
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="movie-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <button className="modal-close" type="button" onClick={onClose} aria-label="Đóng chi tiết phim">×</button>
        <div className="modal-art" style={{ backgroundImage: movie.backdropUrl ? `url("${movie.backdropUrl}")` : undefined }} />
        <div className="modal-content">
          <img className="modal-poster" src={movie.posterUrl} alt={`Poster phim ${movie.displayTitle}`} onError={(event) => { event.currentTarget.src = PLACEHOLDER; }} />
          <div className="modal-info">
            <span className="eyebrow">CHI TIẾT PHIM · MOVIELENS 32M</span>
            <h2 id="modal-title">{movie.displayTitle}</h2>
            {movie.titleVi && movie.titleVi !== movie.displayTitle && <p className="local-title">Tên trên TMDB: {movie.titleVi}</p>}
            <p className="modal-genres">{movie.genresVi.join("  •  ")}</p>
            <div className="modal-metrics">
              {movie.predictionScore !== undefined && movie.predictionScore !== null && <div><span className="metric-label">ĐIỂM ALS DỰ ĐOÁN</span><strong>{movie.predictionScore.toFixed(2).replace(".", ",")}</strong></div>}
              <div><span className="metric-label">ĐIỂM MOVIELENS</span><strong><span className="star">★</span> {ratingText(movie.rating)}</strong></div>
              <div><span className="metric-label">LƯỢT ĐÁNH GIÁ</span><strong>{formatNumber.format(movie.ratingCount)}</strong></div>
              {movie.year && <div><span className="metric-label">NĂM</span><strong>{movie.year}</strong></div>}
            </div>
            <h3>Nội dung phim</h3>
            <p className="overview">{movie.overview || (movie.posterPending ? "Đang tải nội dung phim..." : "Chưa có mô tả cho phim này.")}</p>
            {movie.overviewLang === "en" && <p className="language-note">Mô tả bằng tiếng Anh do TMDB chưa có bản tiếng Việt.</p>}
            <div className="external-links">
              {movie.tmdbUrl && <a href={movie.tmdbUrl} target="_blank" rel="noopener noreferrer">Xem trên TMDB <ArrowIcon /></a>}
              {movie.imdbUrl && <a href={movie.imdbUrl} target="_blank" rel="noopener noreferrer">Trang IMDb <ArrowIcon /></a>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function App() {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [featured, setFeatured] = useState<Movie[]>([]);
  const [featuredPending, setFeaturedPending] = useState(0);
  const [heroIndex, setHeroIndex] = useState(0);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<MoviesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const updateOpenMovie = useCallback((movies: Movie[]) => {
    setSelectedMovie((previous) => {
      const update = movies.find((movie) => movie.movieId === previous?.movieId);
      return previous && update ? { ...previous, ...update } : previous;
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getMeta(controller.signal).then(setMeta).catch(() => undefined);
    getFeatured(controller.signal).then((data) => { setFeatured(data.items); setFeaturedPending(data.pendingPosters); }).catch(() => undefined);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setResults(null);
    getMovies(selectedGenres, search, page, controller.signal)
      .then((data) => { setResults(data); if (data.page !== page) setPage(data.page); })
      .catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Không thể tải danh sách phim."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [selectedGenres, search, page, retry]);

  const resultIds = results?.items.map((movie) => movie.movieId).join(",") ?? "";
  useEffect(() => {
    if (!results?.pendingPosters || !resultIds) return;
    const movieIds = resultIds.split(",").map(Number);
    let active = true;
    const timer = window.setInterval(() => {
      getPosters(movieIds).then((data) => {
        if (!active) return;
        setResults((previous) => {
          if (!previous || previous.items.map((movie) => movie.movieId).join(",") !== resultIds) return previous;
          return { ...previous, items: mergeMovies(previous.items, data.items), pendingPosters: data.pendingPosters };
        });
        updateOpenMovie(data.items);
      }).catch(() => undefined);
    }, 1400);
    return () => { active = false; window.clearInterval(timer); };
  }, [resultIds, results?.pendingPosters]);

  const featuredIds = featured.map((movie) => movie.movieId).join(",");
  useEffect(() => {
    if (!featuredPending || !featuredIds) return;
    const movieIds = featuredIds.split(",").map(Number);
    let active = true;
    const timer = window.setInterval(() => {
      getPosters(movieIds).then((data) => {
        if (!active) return;
        setFeatured((previous) => mergeMovies(previous, data.items));
        setFeaturedPending(data.pendingPosters);
        updateOpenMovie(data.items);
      }).catch(() => undefined);
    }, 1400);
    return () => { active = false; window.clearInterval(timer); };
  }, [featuredIds, featuredPending]);

  function toggleGenre(genre: string) {
    setSelectedGenres((current) => current.includes(genre) ? current.filter((item) => item !== genre) : [...current, genre]);
    setPage(1);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft.trim());
    setPage(1);
    setMobileNavOpen(false);
    scrollToResults();
  }

  function changePage(next: number) {
    setPage(next);
    scrollToResults();
  }

  const heroMovie = featured[heroIndex];
  const nextMovies = featured.map((movie, index) => ({ movie, index })).filter(({ index }) => index !== heroIndex).slice(0, 3);
  const resultStart = results?.total ? (results.page - 1) * results.pageSize + 1 : 0;
  const resultEnd = results ? Math.min(results.page * results.pageSize, results.total) : 0;

  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="#top" aria-label="Cine32, về đầu trang"><FilmMark /><span>CINE<span>32</span></span></a>
          <button className="menu-toggle" type="button" aria-label="Mở menu" aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen(!mobileNavOpen)}>☰</button>
          <nav className={`main-nav ${mobileNavOpen ? "open" : ""}`} aria-label="Điều hướng chính">
            <a href="#discover" onClick={() => setMobileNavOpen(false)}>Khám phá</a>
            <a href="#genres" onClick={() => setMobileNavOpen(false)}>Thể loại</a>
            <a href="#personalized" onClick={() => setMobileNavOpen(false)}>Gợi ý ALS</a>
            <a href="#about" onClick={() => setMobileNavOpen(false)}>Nguồn dữ liệu</a>
          </nav>
          <form className="header-search" role="search" onSubmit={submitSearch}>
            <input value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} placeholder="Tìm tên phim trong MovieLens..." aria-label="Tìm tên phim" />
            {searchDraft && <button className="clear-search" type="button" onClick={() => { setSearchDraft(""); setSearch(""); setPage(1); }} aria-label="Xóa tìm kiếm">×</button>}
            <button className="search-submit" type="submit" aria-label="Tìm phim"><SearchIcon /></button>
          </form>
          <span className="header-source">MOVIELENS <b>32M</b></span>
        </div>
      </header>

      <main id="top">
        <section className="hero-shell" aria-label="Phim nổi bật">
          <div className="hero-main" style={{ backgroundImage: heroMovie?.backdropUrl ? `url("${heroMovie.backdropUrl}")` : undefined }}>
            <div className="hero-shade" />
            <div className="hero-copy">
              <span className="hero-kicker"><span className="kicker-line" /> LỰA CHỌN NỔI BẬT</span>
              <h1>{heroMovie?.displayTitle || "Khám phá thế giới điện ảnh"}</h1>
              <div className="hero-facts">
                {heroMovie?.year && <span>{heroMovie.year}</span>}
                {heroMovie?.rating !== null && heroMovie?.rating !== undefined && <span className="hero-rating"><span className="star">★</span> {ratingText(heroMovie.rating)} <small>MovieLens</small></span>}
                {heroMovie?.genresVi.slice(0, 2).map((genre) => <span key={genre}>{genre}</span>)}
              </div>
              <p>{heroMovie?.overview || "Chọn thể loại bạn yêu thích để khám phá toàn bộ phim phù hợp trong MovieLens 32M."}</p>
              <div className="hero-actions">
                <button className="primary-action" type="button" onClick={() => heroMovie ? setSelectedMovie(heroMovie) : scrollToResults()}>Xem chi tiết <ArrowIcon /></button>
                <button className="text-action" type="button" onClick={scrollToResults}>Khám phá phim <ArrowIcon /></button>
              </div>
            </div>
            {featured.length > 1 && <div className="hero-dots" aria-label="Chọn phim nổi bật">{featured.map((movie, index) => <button key={movie.movieId} type="button" aria-label={`Xem phim nổi bật ${movie.displayTitle}`} aria-current={index === heroIndex ? "true" : undefined} onClick={() => setHeroIndex(index)} />)}</div>}
          </div>
          <aside className="up-next">
            <h2><span>Tiếp theo</span> <ArrowIcon /></h2>
            {nextMovies.map(({ movie, index }) => (
              <button className="up-next-item" type="button" key={movie.movieId} onClick={() => setHeroIndex(index)}>
                <img src={movie.posterUrl} alt="" onError={(event) => { event.currentTarget.src = PLACEHOLDER; }} />
                <span><strong>{movie.displayTitle}</strong><small><span className="star">★</span> {ratingText(movie.rating)} · MovieLens</small></span>
              </button>
            ))}
            <button className="browse-link" type="button" onClick={scrollToResults}>Xem tất cả phim <ArrowIcon /></button>
          </aside>
        </section>

        <section className="stats-strip" aria-label="Thống kê dữ liệu">
          <div><strong>{meta ? formatNumber.format(meta.totalMovies) : "87.585"}</strong><span>phim trong catalog</span></div>
          <div><strong>{meta ? formatNumber.format(meta.ratingCount) : "32M"}</strong><span>lượt đánh giá dùng thống kê</span></div>
          <div><strong>{meta?.genres.length ?? 18}</strong><span>thể loại để khám phá</span></div>
          <p>Điểm đánh giá cộng đồng từ <b>MovieLens 32M</b>.</p>
        </section>

        <section className="discover-section" id="discover">
          <div className="section-heading">
            <div><span className="section-eyebrow">KHÁM PHÁ THEO SỞ THÍCH</span><h2>Chọn phim cho tối nay <ArrowIcon /></h2></div>
            <p>Chọn thể loại để xem mọi phim phù hợp. Phim khớp nhiều thể loại được ưu tiên.</p>
          </div>

          <div id="genres" className="genre-filter" aria-label="Lọc theo thể loại">
            <button type="button" className={`genre-chip ${selectedGenres.length === 0 ? "active" : ""}`} aria-pressed={selectedGenres.length === 0} onClick={() => { setSelectedGenres([]); setPage(1); }}>Tất cả phim</button>
            {meta?.genres.map((genre) => <button type="button" key={genre.id} className={`genre-chip ${selectedGenres.includes(genre.id) ? "active" : ""}`} aria-pressed={selectedGenres.includes(genre.id)} onClick={() => toggleGenre(genre.id)}>{genre.label}</button>)}
          </div>

          <div className="results-toolbar">
            <div className="results-summary">
              <h3>{selectedGenres.length ? "Phim theo thể loại đã chọn" : "Toàn bộ phim"}</h3>
              {search && <button className="search-filter" type="button" onClick={() => { setSearch(""); setSearchDraft(""); setPage(1); }}>Tìm: “{search}” <span>×</span></button>}
              <p>{results ? <><strong>{formatNumber.format(results.total)}</strong> phim · Đang xem {formatNumber.format(resultStart)}–{formatNumber.format(resultEnd)}</> : "Đang tải phim..."}</p>
            </div>
            {results && <Pagination page={results.page} totalPages={results.totalPages} onPageChange={changePage} />}
          </div>

          {error && <div className="error-panel" role="alert">{error} <button type="button" onClick={() => setRetry((current) => current + 1)}>Thử lại</button></div>}
          {loading && !results && <div className="movie-grid" aria-label="Đang tải phim">{Array.from({ length: 12 }, (_, index) => <div className="card-skeleton" key={index}><div /><span /><span /></div>)}</div>}
          {results && <>
            {loading && <div className="loading-line" aria-label="Đang cập nhật kết quả" />}
            {results.items.length ? <div className="movie-grid">{results.items.map((movie) => <MovieCard key={movie.movieId} movie={movie} onOpen={setSelectedMovie} />)}</div> : <div className="empty-panel"><span>⌕</span><h3>Chưa tìm thấy phim phù hợp</h3><p>Thử thể loại hoặc tên phim khác.</p></div>}
            <div className="bottom-pagination"><span>{formatNumber.format(results.total)} phim trong kết quả</span><Pagination page={results.page} totalPages={results.totalPages} onPageChange={changePage} /></div>
          </>}
        </section>
        <PersonalRecommendations renderMovie={(movie) => <MovieCard movie={movie} onOpen={setSelectedMovie} />} onOpen={setSelectedMovie} onMovieUpdate={updateOpenMovie} />
      </main>

      <footer id="about" className="site-footer">
        <div><a className="brand footer-brand" href="#top"><FilmMark /><span>CINE<span>32</span></span></a><p>Khám phá phim theo thể loại trên dữ liệu MovieLens 32M.</p></div>
        <div className="footer-sources"><strong>Nguồn dữ liệu</strong><span>Đánh giá: MovieLens 32M</span><span>Poster và mô tả: TMDB</span><small>This product uses the TMDB API but is not endorsed or certified by TMDB.</small></div>
      </footer>

      {selectedMovie && <MovieModal movie={selectedMovie} onClose={() => setSelectedMovie(null)} />}
    </>
  );
}

export default App;
