import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { getDemoRecommendations, getPosters } from "./api";
import { useDemoProfiles } from "./DemoProfiles";
import type { DemoRecommendationsResponse, Movie } from "./types";

export default function DemoRecommendations({ renderMovie, onOpen, onMovieUpdate }: {
  renderMovie: (movie: Movie) => ReactNode;
  onOpen: (movie: Movie) => void;
  onMovieUpdate: (movies: Movie[]) => void;
}) {
  const { profiles, activeProfile, createProfile, selectProfile, markWatched, error: storageError } = useDemoProfiles();
  const [name, setName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [formError, setFormError] = useState("");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState<{ profileId: string; historyKey: string; data: DemoRecommendationsResponse } | null>(null);
  const profileId = activeProfile?.id ?? "";
  const historyKey = activeProfile?.watched.map(movie => movie.movieId).join(",") ?? "";
  const data = result?.profileId === profileId && result.historyKey === historyKey ? result.data : null;

  useEffect(() => {
    if (!profileId) return;
    const controller = new AbortController();
    setError("");
    getDemoRecommendations(historyKey ? historyKey.split(",").map(Number) : [], controller.signal)
      .then(data => { if (!controller.signal.aborted) setResult({ profileId, historyKey, data }); })
      .catch(failure => { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Không thể tải gợi ý."); });
    return () => controller.abort();
  }, [profileId, historyKey, retry]);

  const pendingIds = data ? [...data.items, ...data.history].filter(movie => movie.posterPending).map(movie => movie.movieId).join(",") : "";
  useEffect(() => {
    if (!pendingIds) return;
    const controller = new AbortController();
    const ids = [...new Set(pendingIds.split(",").map(Number))];
    const timer = window.setInterval(() => {
      getPosters(ids, controller.signal).then(updates => {
        if (controller.signal.aborted) return;
        const byId = new Map(updates.items.map(movie => [movie.movieId, movie]));
        const merge = (movies: Movie[]) => movies.map(movie => ({ ...movie, ...byId.get(movie.movieId) }));
        setResult(previous => previous?.profileId === profileId && previous.historyKey === historyKey ? {
          ...previous, data: { ...previous.data, items: merge(previous.data.items), history: merge(previous.data.history), pendingPosters: updates.pendingPosters },
        } : previous);
        onMovieUpdate(updates.items);
      }).catch(() => undefined);
    }, 1400);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [pendingIds, profileId, historyKey, onMovieUpdate]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try { createProfile(name); setName(""); setFormError(""); setShowCreate(false); }
    catch (failure) { setFormError(failure instanceof Error ? failure.message : "Không thể tạo hồ sơ."); }
  }

  return <section className="discover-section demo-profile-section" id="personalized" aria-labelledby="demo-profile-title">
    <div className="section-heading">
      <div><span className="section-eyebrow">GU PHIM CỦA RIÊNG BẠN</span><h2 id="demo-profile-title">Phim dành cho bạn</h2></div>
      <p>Tạo hồ sơ và đánh dấu những phim đã xem. CINE32 sẽ gợi ý theo thể loại bạn xem nhiều nhất.</p>
    </div>
    <div className="profile-toolbar">
      {profiles.length > 0 && <div className="profile-switcher"><label htmlFor="demo-profile-select">Đang sử dụng hồ sơ</label><select id="demo-profile-select" value={profileId} onChange={event => selectProfile(event.target.value)}>{profiles.map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</select></div>}
      {profiles.length > 0 && <button type="button" className="profile-create-toggle" onClick={() => { setShowCreate(!showCreate); setFormError(""); }}>{showCreate ? "Đóng tạo hồ sơ" : "+ Tạo user mới"}</button>}
      <span className="profile-demo-label">HỒ SƠ DEMO · LƯU TRÊN TRÌNH DUYỆT NÀY</span>
    </div>
    {(showCreate || profiles.length === 0) && <form className="profile-create-form" onSubmit={submit}>
      <div><label htmlFor="demo-profile-name">Tên người dùng</label><input id="demo-profile-name" value={name} onChange={event => setName(event.target.value)} maxLength={40} required placeholder="Ví dụ: Minh, An, Lan..." autoComplete="off" /></div>
      <button type="submit" className="primary-action">Tạo hồ sơ</button>
      <p>Mỗi hồ sơ có lịch sử và gợi ý riêng. Bản trình diễn không yêu cầu mật khẩu.</p>
      {formError && <p className="profile-form-error" role="alert">{formError}</p>}
    </form>}
    {storageError && <p className="profile-form-error" role="alert">{storageError}</p>}
    {!activeProfile && <div className="profile-welcome"><span>01</span><p>Tạo hồ sơ của bạn, mở chi tiết một phim rồi bấm <strong>“Đánh dấu đã xem”</strong> để bắt đầu.</p></div>}
    {activeProfile && <>
      <div className="profile-overview">
        <div className="profile-identity"><span className="profile-avatar">{activeProfile.name[0].toLocaleUpperCase("vi")}</span><div><h3>Xin chào, {activeProfile.name}</h3><p><strong>{activeProfile.watched.length}</strong> phim đã xem <span>·</span> <a href="#discover">Chọn thêm phim</a></p></div></div>
        <div className="profile-tastes"><h3>Thể loại bạn xem nhiều</h3>{data?.genres.length ? <><div className="profile-genre-chips">{data.genres.slice(0, 5).map(genre => <span key={genre.id}>{genre.label}<strong>{genre.count} phim</strong></span>)}</div><small>Một phim có nhiều thể loại được tính vào từng thể loại tương ứng.</small></> : <p>{data ? "Đánh dấu vài phim đã xem để khám phá gu phim của bạn." : "Đang cập nhật thể loại..."}</p>}</div>
      </div>
      {error && <div className="error-panel" role="alert">{error} <button type="button" onClick={() => setRetry(value => value + 1)}>Thử lại</button></div>}
      {!data && !error && <p className="personal-loading" role="status">Đang cập nhật gợi ý cho {activeProfile.name}...</p>}
      {data && <>
        <div className="personal-result-heading" aria-live="polite"><h3>Gợi ý cho {activeProfile.name}</h3><p>{data.message}</p></div>
        {data.items.length ? <div className="movie-grid">{data.items.map(movie => <div className="personal-card" key={movie.movieId}>{renderMovie(movie)}</div>)}</div> : <div className="empty-panel">Chưa còn phim phù hợp chưa xem. Thử khám phá thêm thể loại khác.</div>}
        {data.history.length > 0 && <details className="history-panel demo-watch-history"><summary>Lịch sử của {activeProfile.name} · {activeProfile.watched.length} phim đã xem</summary><p>Hiển thị tối đa 12 phim được đánh dấu gần nhất.</p><div className="demo-history-list">{data.history.map(movie => <div key={movie.movieId}><button type="button" className="history-movie-title" onClick={() => onOpen(movie)}>{movie.displayTitle}</button><span>{movie.genresVi.join(" · ")}</span><button type="button" className="history-remove" aria-label={`Bỏ đã xem ${movie.displayTitle}`} onClick={() => markWatched(movie.movieId, false)}>Bỏ đã xem</button></div>)}</div></details>}
      </>}
    </>}
  </section>;
}
