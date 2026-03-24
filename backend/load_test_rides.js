/**
 * load_test_rides.js — k6 load test שכבה 2: create ride + search + book
 *
 * לפני הרצה — וודא ב-backend/.env:
 *   DEBUG=True  (כדי שאימות אימייל יהיה אוטומטי לmשתמשי הtest)
 *
 * הרצה:
 *   k6 run --vus 5 --duration 30s backend\load_test_rides.js
 *
 * הגבלת VUs ל-5 בלבד כי כל iteration עושה:
 *   1. login (DB)
 *   2. preview-routes (geocoding חיצוני — נמנע עם קואורדינטות ישירות)
 *   3. create ride (DB write + Redis + outbox)
 *   4. search rides (PostGIS query)
 * סה"כ: 4 בקשות per iteration, כבד יותר מauth
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000/api/v1";

// ─── Metrics ──────────────────────────────────────────────────────────────────
const loginErrors = new Rate("login_errors");
const previewErrors = new Rate("preview_errors");
const createErrors = new Rate("create_errors");
const searchErrors = new Rate("search_errors");

const loginDuration = new Trend("login_duration", true);
const previewDuration = new Trend("preview_duration", true);
const createDuration = new Trend("create_duration", true);
const searchDuration = new Trend("search_duration", true);

// ─── Options ──────────────────────────────────────────────────────────────────
export const options = {
  thresholds: {
    login_duration: ["p(95)<1000"],
    preview_duration: ["p(95)<3000"],
    create_duration: ["p(95)<3000"],
    search_duration: ["p(95)<5000"],
    login_errors: ["rate<0.05"],
    preview_errors: ["rate<0.05"],
    create_errors: ["rate<0.05"],
    search_errors: ["rate<0.10"], // search יותר מחמיר בגלל PostGIS
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const HEADERS = { "Content-Type": "application/json" };

let userCounter = 0;

function uniqueUser() {
  userCounter++;
  const vuSuffix = `${__VU}_${__ITER}_${userCounter}`;
  return {
    email: `rides_test_${vuSuffix}@loadtest.linkup.co.il`,
    password: "TestPass123!",
    full_name: "Load Test Driver",
    phone_number: `+97250${String(8000000 + __VU * 10000 + __ITER).padStart(7, "0")}`,
    confirm_password: "TestPass123!",
  };
}

// קואורדינטות קבועות — תל אביב → ירושלים
// שולחים lat/lon ישירות כדי לדלג על geocoding חיצוני לחלוטין
const ORIGIN = {
  lat: 32.0853,
  lon: 34.7818,
  name: "תל אביב, ישראל",
};
const DESTINATION = {
  lat: 31.7683,
  lon: 35.2137,
  name: "ירושלים, ישראל",
};

function departureTime() {
  // זמן עתידי: עכשיו + 2 שעות
  return new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
}

// ─── Main scenario ─────────────────────────────────────────────────────────────
export default function () {
  const user = uniqueUser();
  const headers = HEADERS;

  // ── שלב 0: Register ──────────────────────────────────────────────────────────
  const regRes = http.post(`${BASE_URL}/auth/register`, JSON.stringify(user), { headers });
  if (regRes.status !== 201) {
    console.error(`[register FAIL] status=${regRes.status} body=${regRes.body?.substring(0, 300)}`);
    sleep(1);
    return;
  }

  // ── שלב 1: Login ─────────────────────────────────────────────────────────────
  const loginStart = Date.now();
  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    { headers }
  );
  loginDuration.add(Date.now() - loginStart);

  const loginOk = check(loginRes, {
    "login: status 200": (r) => r.status === 200,
    "login: has token": (r) => {
      try {
        return !!JSON.parse(r.body).access_token;
      } catch {
        return false;
      }
    },
  });
  loginErrors.add(!loginOk);

  if (!loginOk) {
    console.error(`[login FAIL] status=${loginRes.status} body=${loginRes.body?.substring(0, 200)}`);
    sleep(1);
    return;
  }

  const token = JSON.parse(loginRes.body).access_token;
  const userId = JSON.parse(loginRes.body).user.user_id;
  const authHeaders = { ...headers, Authorization: `Bearer ${token}` };

  // ── שלב 2: Preview route (קואורדינטות ישירות — אפס geocoding) ───────────────
  const previewStart = Date.now();
  const previewRes = http.post(
    `${BASE_URL}/rides/preview-routes`,
    JSON.stringify({
      driver_id: userId,
      origin_lat: ORIGIN.lat,
      origin_lon: ORIGIN.lon,
      destination_name: DESTINATION.name,
      departure_time: departureTime(),
      available_seats: 3,
      price: 25.0,
    }),
    { headers: authHeaders }
  );
  previewDuration.add(Date.now() - previewStart);

  const previewOk = check(previewRes, {
    "preview: status 200": (r) => r.status === 200,
    "preview: has session_id": (r) => {
      try {
        return !!JSON.parse(r.body).session_id;
      } catch {
        return false;
      }
    },
  });
  previewErrors.add(!previewOk);

  if (!previewOk) {
    console.error(`[preview FAIL] status=${previewRes.status} body=${previewRes.body?.substring(0, 300)}`);
    sleep(1);
    return;
  }

  const sessionId = JSON.parse(previewRes.body).session_id;

  // ── שלב 3: Create ride ────────────────────────────────────────────────────────
  const createStart = Date.now();
  const createRes = http.post(
    `${BASE_URL}/rides/`,
    JSON.stringify({
      session_id: sessionId,
      selected_route_index: 0,
    }),
    { headers: authHeaders }
  );
  createDuration.add(Date.now() - createStart);

  const createOk = check(createRes, {
    "create ride: status 201": (r) => r.status === 201,
    "create ride: has ride_id": (r) => {
      try {
        return !!JSON.parse(r.body).ride_id;
      } catch {
        return false;
      }
    },
  });
  createErrors.add(!createOk);

  if (!createOk) {
    console.error(`[create FAIL] status=${createRes.status} body=${createRes.body?.substring(0, 300)}`);
    sleep(0.5);
  }

  // ── שלב 4: Search rides (PostGIS query) ──────────────────────────────────────
  // search דורש geocoding — נשתמש בשמות קצרים שGoogle מחזיר מ-cache מהיר
  // 2 קריאות geocoding per search — זול יחסית
  const searchStart = Date.now();
  const searchUrl = `${BASE_URL}/passenger/passengers/search-rides?pickup_name=${encodeURIComponent("תל אביב")}&destination_name=${encodeURIComponent("ירושלים")}&search_radius=5000&limit=10`;
  console.log(`[search URL] ${searchUrl}`);
  const searchRes = http.get(searchUrl, { headers: authHeaders });
  searchDuration.add(Date.now() - searchStart);

  const searchOk = check(searchRes, {
    "search: status 200": (r) => r.status === 200,
    "search: has items": (r) => {
      try {
        return Array.isArray(JSON.parse(r.body).items);
      } catch {
        return false;
      }
    },
  });
  searchErrors.add(!searchOk);

  if (!searchOk) {
    console.error(`[search FAIL] status=${searchRes.status} body=${searchRes.body?.substring(0, 300)}`);
  }

  sleep(1);
}

// ─── Summary ──────────────────────────────────────────────────────────────────
export function handleSummary(data) {
  const m = data.metrics;
  console.log("\n=== LINKUP RIDES LOAD TEST SUMMARY ===");

  if (m.login_duration) console.log(`/login    p95: ${m.login_duration.values["p(95)"]?.toFixed(0)}ms`);
  if (m.preview_duration)
    console.log(`/preview  p95: ${m.preview_duration.values["p(95)"]?.toFixed(0)}ms`);
  if (m.create_duration) console.log(`/create   p95: ${m.create_duration.values["p(95)"]?.toFixed(0)}ms`);
  if (m.search_duration) console.log(`/search   p95: ${m.search_duration.values["p(95)"]?.toFixed(0)}ms`);

  const failed = m.http_req_failed;
  if (failed) {
    const rate = (failed.values.rate * 100).toFixed(2);
    console.log(`Error rate: ${rate}% ${failed.values.rate < 0.05 ? "✅" : "❌"}`);
  }

  return {};
}
