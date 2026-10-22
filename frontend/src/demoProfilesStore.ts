export const DEMO_STORAGE_KEY = "cine32.demo.profiles.v1";
export const MAX_PROFILES = 12;
export const MAX_WATCHED = 1000;

export interface WatchedMovie { movieId: number; watchedAt: number }
export interface DemoProfile { id: string; name: string; createdAt: number; watched: WatchedMovie[] }
export interface DemoState { version: 1; profiles: DemoProfile[]; activeId: string | null }

export function emptyDemoState(): DemoState { return { version: 1, profiles: [], activeId: null }; }

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validMovieId(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0 && value <= 2147483647;
}

export function parseDemoState(raw: string | null): DemoState {
  try {
    const parsed: unknown = JSON.parse(raw ?? "null");
    if (!record(parsed) || parsed.version !== 1 || !Array.isArray(parsed.profiles)) return emptyDemoState();
    const profiles: DemoProfile[] = [];
    for (const candidate of parsed.profiles.slice(0, MAX_PROFILES)) {
      if (!record(candidate) || typeof candidate.id !== "string" || !candidate.id || candidate.id.length > 100 || typeof candidate.name !== "string" || !candidate.name.trim() || candidate.name.trim().length > 40 || !Array.isArray(candidate.watched) || profiles.some(profile => profile.id === candidate.id)) continue;
      const watched = new Map<number, WatchedMovie>();
      for (const item of candidate.watched.slice(0, MAX_WATCHED)) {
        if (record(item) && validMovieId(item.movieId) && typeof item.watchedAt === "number" && Number.isFinite(item.watchedAt)) {
          watched.set(item.movieId, { movieId: item.movieId, watchedAt: item.watchedAt });
        }
      }
      profiles.push({ id: candidate.id, name: candidate.name.trim(), createdAt: typeof candidate.createdAt === "number" && Number.isFinite(candidate.createdAt) ? candidate.createdAt : 0, watched: [...watched.values()] });
    }
    return { version: 1, profiles, activeId: profiles.some(profile => profile.id === parsed.activeId) ? parsed.activeId as string : profiles[0]?.id ?? null };
  } catch { return emptyDemoState(); }
}

export function addDemoProfile(state: DemoState, id: string, name: string, now = Date.now()): DemoState {
  const clean = name.trim();
  if (!clean || clean.length > 40) throw new Error("Nhập tên hồ sơ từ 1 đến 40 ký tự.");
  if (state.profiles.length >= MAX_PROFILES) throw new Error("Bản demo hỗ trợ tối đa 12 hồ sơ trên trình duyệt này.");
  if (state.profiles.some(profile => profile.name.toLocaleLowerCase("vi") === clean.toLocaleLowerCase("vi") || profile.id === id)) throw new Error("Tên hồ sơ này đã có. Hãy chọn tên khác.");
  return { version: 1, profiles: [...state.profiles, { id, name: clean, createdAt: now, watched: [] }], activeId: id };
}

export function selectDemoProfile(state: DemoState, id: string): DemoState {
  return state.profiles.some(profile => profile.id === id) ? { ...state, activeId: id } : state;
}

export function setMovieWatched(state: DemoState, profileId: string, movieId: number, watched: boolean, now = Date.now()): DemoState {
  if (!validMovieId(movieId)) throw new Error("Mã phim không hợp lệ.");
  const profile = state.profiles.find(value => value.id === profileId);
  if (!profile) return state;
  const exists = profile.watched.some(value => value.movieId === movieId);
  if (exists === watched) return state;
  if (watched && profile.watched.length >= MAX_WATCHED) throw new Error("Hồ sơ demo đã đủ 1.000 phim. Bỏ đánh dấu một phim để thêm phim khác.");
  return { ...state, profiles: state.profiles.map(value => value.id !== profileId ? value : { ...value, watched: watched ? [...value.watched, { movieId, watchedAt: now }] : value.watched.filter(item => item.movieId !== movieId) }) };
}
