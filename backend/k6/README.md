# k6 Load Tests

Central location for backend load/performance tests.

## Structure

- `scripts/` - scenario files by layer
- `lib/` - shared helpers (`helpers.js`, `options.js`)

## Scenario options (`lib/options.js`)

All scripts use `buildOptions(thresholds, defaultStages)`:

- **Stages (default):** `k6 run …/load_test_*.js` — ramp from each script’s `defaultStages` (auth uses a heavier ramp than the others).
- **Flat load:** set **both** `VUS` and `DURATION` via env, e.g.  
  `k6 run -e VUS=50 -e DURATION=1m backend/k6/scripts/load_test_groups.js`  
  (`BASE_URL` etc. still work the same.)

You can still use k6 CLI flags such as `--vus` / `--duration` where they apply; they may override parts of `export const options` depending on your k6 version.

## Layers

- `scripts/load_test_auth.js` - Layer 1 (Auth)
- `scripts/load_test_rides.js` - Layer 2 (Core flows: preview/create/search/join/approve/reject/cancel)
- `scripts/load_test_users.js` - Layer 3 (Users/Profile)
- `scripts/load_test_groups.js` - Layer 4 (Groups)
- `scripts/load_test_chat.js` - Layer 5 (Chat HTTP)
- `scripts/load_test_geo.js` - Layer 6 (Geo/Maps integration pressure)
- `scripts/load_test_ws.js` - Layer 7 (WebSocket/realtime)

## Run

From repo root:

```bash
k6 run backend/k6/scripts/load_test_auth.js
k6 run backend/k6/scripts/load_test_rides.js
k6 run backend/k6/scripts/load_test_users.js
k6 run backend/k6/scripts/load_test_groups.js
k6 run backend/k6/scripts/load_test_chat.js
k6 run backend/k6/scripts/load_test_geo.js
k6 run backend/k6/scripts/load_test_ws.js
```

## Results convention

- Save test outputs under `backend/k6/results/<script_name>/`.
- Example for rides: `backend/k6/results/load_test_rides/results-YYYYMMDD-HHMMSS.txt`.
- The repository keeps the folder structure (`.gitkeep`), while generated result files are ignored by `.gitignore`.

Optional environment overrides:

- `BASE_URL` (default `http://localhost:8000/api/v1`)
- `WS_URL` (default `ws://localhost:8081/ws`)
- `PRESENCE_URL` (default `http://localhost:8081/presence`)
- `USER_PUBLIC_PATH` (default `/users/{id}`)

## Prerequisites

- Backend and dependencies up
- `DEBUG=True` in `backend/.env` for easier registration/login in load users
- If auth limits are active, raise `RATE_LIMIT_AUTH_MAX_REQUESTS` for test windows
