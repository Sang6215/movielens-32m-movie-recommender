import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { addDemoProfile, DEMO_STORAGE_KEY, emptyDemoState, parseDemoState, selectDemoProfile, setMovieWatched, type DemoProfile } from "./demoProfilesStore";

interface DemoProfilesContext {
  profiles: DemoProfile[];
  activeProfile: DemoProfile | null;
  createProfile: (name: string) => void;
  selectProfile: (id: string) => void;
  markWatched: (movieId: number, watched: boolean) => void;
  isWatched: (movieId: number) => boolean;
  error: string;
}

const ProfilesContext = createContext<DemoProfilesContext | null>(null);

export function DemoProfilesProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(() => {
    try { return parseDemoState(localStorage.getItem(DEMO_STORAGE_KEY)); }
    catch { return emptyDemoState(); }
  });
  const [error, setError] = useState("");
  const activeProfile = state.profiles.find(profile => profile.id === state.activeId) ?? null;

  useEffect(() => {
    try { localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(state)); setError(""); }
    catch { setError("Trình duyệt đang chặn hoặc đã đầy bộ nhớ lưu hồ sơ. Lịch sử hiện tại có thể mất khi tải lại trang."); }
  }, [state]);

  useEffect(() => {
    function update(event: StorageEvent) {
      if (event.key === DEMO_STORAGE_KEY) setState(parseDemoState(event.newValue));
    }
    window.addEventListener("storage", update);
    return () => window.removeEventListener("storage", update);
  }, []);

  function createProfile(name: string) {
    setState(addDemoProfile(state, crypto.randomUUID(), name));
  }

  function markWatched(movieId: number, watched: boolean) {
    if (!activeProfile) return;
    try { setState(setMovieWatched(state, activeProfile.id, movieId, watched)); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Không thể lưu phim."); }
  }

  return <ProfilesContext.Provider value={{ profiles: state.profiles, activeProfile, createProfile, selectProfile: id => setState(previous => selectDemoProfile(previous, id)), markWatched, isWatched: movieId => activeProfile?.watched.some(movie => movie.movieId === movieId) ?? false, error }}>{children}</ProfilesContext.Provider>;
}

export function useDemoProfiles() {
  const value = useContext(ProfilesContext);
  if (!value) throw new Error("DemoProfilesProvider is missing");
  return value;
}

export function WatchedButton({ movieId, onCreateProfile }: { movieId: number; onCreateProfile?: () => void }) {
  const { activeProfile, isWatched, markWatched } = useDemoProfiles();
  const watched = isWatched(movieId);
  if (!activeProfile) return <a className="watch-create-link" href="#personalized" onClick={onCreateProfile}>Tạo hồ sơ để lưu phim đã xem</a>;
  return <div className="watch-action"><button type="button" className={`watch-button ${watched ? "is-watched" : ""}`} aria-pressed={watched} onClick={() => markWatched(movieId, !watched)}>{watched ? "✓ Đã xem — Bỏ đánh dấu" : "+ Đánh dấu đã xem"}</button><small>Lưu vào hồ sơ {activeProfile.name}. Gợi ý sẽ cập nhật theo thể loại của phim.</small></div>;
}
