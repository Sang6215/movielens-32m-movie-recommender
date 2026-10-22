import assert from "node:assert/strict";
import test from "node:test";
import { addDemoProfile, emptyDemoState, parseDemoState, selectDemoProfile, setMovieWatched } from "../src/demoProfilesStore.ts";

test("switching profiles isolates histories and reload preserves them", () => {
  let state = addDemoProfile(emptyDemoState(), "user-a", "Minh", 1);
  state = setMovieWatched(state, "user-a", 1, true, 2);
  state = addDemoProfile(state, "user-b", "Lan", 3);
  state = setMovieWatched(state, "user-b", 2, true, 4);
  state = selectDemoProfile(parseDemoState(JSON.stringify(state)), "user-a");
  assert.equal(state.activeId, "user-a");
  assert.deepEqual(state.profiles[0].watched, [{ movieId: 1, watchedAt: 2 }]);
  assert.deepEqual(state.profiles[1].watched, [{ movieId: 2, watchedAt: 4 }]);
});

test("marking twice is idempotent, removing affects only the selected user", () => {
  let state = addDemoProfile(emptyDemoState(), "a", "An", 1);
  state = addDemoProfile(state, "b", "Bình", 2);
  state = setMovieWatched(state, "a", 318, true, 3);
  state = setMovieWatched(state, "b", 318, true, 4);
  assert.strictEqual(setMovieWatched(state, "a", 318, true, 5), state);
  const removed = setMovieWatched(state, "a", 318, false, 6);
  assert.equal(removed.profiles[0].watched.length, 0);
  assert.equal(removed.profiles[1].watched.length, 1);
  assert.equal(state.profiles[0].watched.length, 1);
});

test("malformed storage and duplicate records cannot inflate watch counts", () => {
  assert.deepEqual(parseDemoState("{not-json"), emptyDemoState());
  const state = parseDemoState(JSON.stringify({ version: 1, activeId: "missing", profiles: [{ id: "a", name: " An ", watched: [{ movieId: 1, watchedAt: 1 }, { movieId: 1, watchedAt: 2 }, { movieId: -1, watchedAt: 3 }, { movieId: "2", watchedAt: 4 }] }] }));
  assert.equal(state.activeId, "a");
  assert.equal(state.profiles[0].name, "An");
  assert.deepEqual(state.profiles[0].watched, [{ movieId: 1, watchedAt: 2 }]);
});

test("profile names are validated and history limit cannot discard old watches", () => {
  let state = addDemoProfile(emptyDemoState(), "a", "Minh", 1);
  assert.throws(() => addDemoProfile(state, "b", " minh "), /đã có/);
  assert.throws(() => addDemoProfile(state, "b", "   "), /1 đến 40/);
  assert.throws(() => setMovieWatched(state, "a", 0, true), /không hợp lệ/);
  for (let movieId = 1; movieId <= 1000; movieId++) state = setMovieWatched(state, "a", movieId, true, movieId);
  assert.throws(() => setMovieWatched(state, "a", 1001, true), /1.000/);
  assert.equal(state.profiles[0].watched.length, 1000);
});
