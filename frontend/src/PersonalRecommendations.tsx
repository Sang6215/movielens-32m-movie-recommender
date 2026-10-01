import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { getALSMeta, getPersonalRecommendations, getPosters } from "./api";
import type { ALSMetaResponse, Movie, PersonalResponse } from "./types";

const formatNumber = new Intl.NumberFormat("vi-VN");

export default function PersonalRecommendations({ renderMovie, onOpen, onMovieUpdate }: {
  renderMovie: (movie: Movie) => ReactNode;
  onOpen: (movie: Movie) => void;
  onMovieUpdate: (movies: Movie[]) => void;
}) {
  const [meta, setMeta] = useState<ALSMetaResponse | null>(null);
  const [draft, setDraft] = useState("1");
  const [userId, setUserId] = useState(1);
  const [data, setData] = useState<PersonalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getALSMeta(controller.signal).then(setMeta).catch(() => undefined);
    return () => controller.abort();
  }, [retry]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
    setLoading(true);
    getPersonalRecommendations(userId, controller.signal)
      .then(setData)
      .catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Không thể tải gợi ý."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [userId, retry]);

  const pendingIds = data ? [...data.items, ...data.history].filter((movie) => movie.posterPending).map((movie) => movie.movieId).join(",") : "";
  useEffect(() => {
    if (!pendingIds) return;
    const controller = new AbortController();
    const ids = [...new Set(pendingIds.split(",").map(Number))];
    const timer = window.setInterval(() => {
      getPosters(ids, controller.signal).then((updates) => {
        if (controller.signal.aborted) return;
        const byId = new Map(updates.items.map((movie) => [movie.movieId, movie]));
        const merge = (movies: Movie[]) => movies.map((movie) => ({ ...movie, ...byId.get(movie.movieId) }));
        setData((previous) => previous?.userId === userId ? { ...previous, items: merge(previous.items), history: merge(previous.history), pendingPosters: updates.pendingPosters } : previous);
        onMovieUpdate(updates.items);
      }).catch(() => undefined);
    }, 1400);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [pendingIds, userId, onMovieUpdate]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = Number(draft);
    if (!draft.trim() || !Number.isInteger(id) || id < 0 || id > 2147483647) return;
    setUserId(id);
  }

  function selectUser(id: number) {
    setDraft(String(id));
    setUserId(id);
  }

  return (
    <section className="discover-section personal-section" id="personalized" aria-labelledby="personal-title">
      <div className="section-heading">
        <div><span className="section-eyebrow">GỢI Ý CÁ NHÂN</span><h2 id="personal-title">Phim dành cho bạn</h2></div>
        <p>Chọn một người dùng MovieLens để khám phá 10 phim mới dựa trên lịch sử đánh giá.</p>
      </div>
      <div className="personal-controls">
        <form className="user-form" onSubmit={submit}>
          <label htmlFor="als-user-id">User ID MovieLens</label>
          <div><input id="als-user-id" type="number" min="0" max="2147483647" step="1" required value={draft} onChange={(event) => setDraft(event.target.value)} /><button className="primary-action" type="submit">Xem Top 10</button></div>
        </form>
        <div className="example-users"><span>Thử nhanh:</span>{(meta?.exampleUserIds ?? [1, 2, 3]).slice(0, 3).map((id) => <button type="button" className="genre-chip" key={id} aria-pressed={userId === id} onClick={() => selectUser(id)}>User {id}</button>)}<button type="button" className="genre-chip" aria-pressed={userId === 0} onClick={() => selectUser(0)}>Người dùng mới</button></div>
      </div>
      {meta && <p className="personal-method">ALS · {formatNumber.format(meta.users)} người dùng · {formatNumber.format(meta.candidateMovies)} phim có ít nhất {meta.minRatingCount} lượt đánh giá. Model đã train {meta.selectedParams.maxIter} vòng; RMSE test {meta.testRatingMetrics.rmse.toFixed(4)}.</p>}
      {error && <div className="error-panel" role="alert">{error} <button type="button" onClick={() => setRetry((value) => value + 1)}>Thử lại</button></div>}
      {loading && <p className="personal-loading" role="status">Đang tìm phim phù hợp...</p>}
      {data && <>
        <div className="personal-result-heading" aria-live="polite"><h3>{data.knownUser ? `Top 10 cho User ${data.userId}` : "Phim cho người dùng mới"}</h3><p>{data.message} {data.knownUser && `Đã loại ${formatNumber.format(data.historyCount)} lượt đánh giá trong lịch sử.`}</p></div>
        {data.items.length ? <div className="movie-grid">{data.items.map((movie) => <div className="personal-card" key={movie.movieId}>{renderMovie(movie)}</div>)}</div> : <div className="empty-panel">Người dùng đã đánh giá hết phim trong tập ứng viên.</div>}
        {data.knownUser && <p className="personal-score-note">Điểm ALS là ước lượng của model, có thể nằm ngoài khoảng 0,5–5. Điểm MovieLens là điểm trung bình cộng đồng.</p>}
        {data.history.length > 0 && <details className="history-panel"><summary>Lịch sử đã đánh giá của User {data.userId} · Xem 12 phim gần nhất</summary><div className="history-list">{data.history.map((movie) => <button type="button" key={movie.movieId} onClick={() => onOpen(movie)}><span>{movie.displayTitle}</span><strong>★ {movie.historyRating?.toFixed(1).replace(".", ",")}/5</strong></button>)}</div></details>}
      </>}
    </section>
  );
}
