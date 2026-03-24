// k6 load test — auth register + login
//
// לפני הרצת load test — עדכן backend/.env:
//   RATE_LIMIT_AUTH_MAX_REQUESTS=10000
//   DEBUG=True   ← כדי שאימות אימייל יהיה אוטומטי
// אחרי הבדיקה — החזר לערכים המקוריים.
//
// Prerequisites: backend up (e.g. docker-compose), manual register works in Swagger.
// Run from this directory: k6 run load_test.js
// Or from repo root: k6 run backend/load_test.js

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ============================================================
// הגדרות בסיסיות
// ============================================================
const BASE = "http://localhost:8000";
const AUTH = "/api/v1/auth";

// מטריקות מותאמות
const registerErrors = new Rate("register_errors");
const loginErrors = new Rate("login_errors");
const registerDuration = new Trend("register_duration", true);
const loginDuration = new Trend("login_duration", true);

// ============================================================
// תרחיש העומס — 3 שלבים
// ramp up → שיא → ramp down
// ============================================================
export const options = {
  stages: [
    { duration: "30s", target: 50 },   // עלייה הדרגתית ל-50 משתמשים
    { duration: "1m",  target: 200 },  // עלייה ל-200 משתמשים
    { duration: "1m",  target: 500 },  // שיא — 500 concurrent
    { duration: "30s", target: 0 },    // ירידה
  ],
  thresholds: {
    // ספי הצלחה — אם חורגים, הבדיקה נכשלת
    "register_errors":        ["rate<0.05"],   // פחות מ-5% שגיאות ברישום
    "login_errors":           ["rate<0.05"],   // פחות מ-5% שגיאות בלוגין
    "register_duration":      ["p(95)<3000"],  // 95% מהרישומים תחת 3 שניות
    "login_duration":         ["p(95)<1500"],  // 95% מהלוגינים תחת 1.5 שניות
    "http_req_failed":        ["rate<0.05"],   // פחות מ-5% שגיאות HTTP כלליות
  },
};

// ============================================================
// פונקציות עזר
// ============================================================

// מספרים +972508XXXXXXX (050-8…) — טווח שעובר is_valid_number
// __VU + __ITER מבטיחים ייחודיות בין כל האיטרציות בכל ה-VU-ים (כל עוד __ITER < 10000 לכל VU)
function randomPhone() {
  const vuId = __VU * 10000 + __ITER;
  const suffix = String(8000000 + vuId).padStart(7, "0");
  return `+97250${suffix}`;
}

// יוצר משתמש ייחודי לכל iteration (כדי לא לפגוע ב-unique constraint)
function uniqueUser() {
  const id = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  return {
    full_name: `Test User ${id}`,
    email: `test_${id}@loadtest.com`,
    phone_number: randomPhone(),
    password: "Test@1234!",
    confirm_password: "Test@1234!",
  };
}

const headers = { "Content-Type": "application/json" };

// ============================================================
// תרחיש ראשי — כל VU מריץ את זה בלופ
// ============================================================
export default function () {
  const user = uniqueUser();

  // --- שלב 1: רישום ---
  const registerRes = http.post(
    `${BASE}${AUTH}/register`,
    JSON.stringify(user),
    { headers }
  );

  registerDuration.add(registerRes.timings.duration);

  const registerOk = check(registerRes, {
    "register: status 201":     (r) => r.status === 201,
    "register: has user_id":    (r) => {
      try { return !!JSON.parse(r.body).user_id; } catch { return false; }
    },
  });

  registerErrors.add(!registerOk);

  if (!registerOk) {
    // לוג מפורט על כישלון — עוזר לזהות את הבעיה
    console.error(`[register FAIL] status=${registerRes.status} body=${registerRes.body?.slice(0, 200)}`);
    sleep(1);
    return; // אין טעם להמשיך ללוגין אם הרישום נכשל
  }

  sleep(0.5); // המתנה קצרה בין רישום ללוגין (מדמה התנהגות אמיתית)

  // --- שלב 2: לוגין עם אותו משתמש ---
  const loginRes = http.post(
    `${BASE}${AUTH}/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    { headers }
  );

  loginDuration.add(loginRes.timings.duration);

  const loginOk = check(loginRes, {
    "login: status 200":            (r) => r.status === 200,
    "login: has access_token":      (r) => {
      try { return !!JSON.parse(r.body).access_token; } catch { return false; }
    },
    "login: has refresh_token":     (r) => {
      try { return !!JSON.parse(r.body).refresh_token; } catch { return false; }
    },
  });

  loginErrors.add(!loginOk);

  if (!loginOk) {
    console.error(`[login FAIL] status=${loginRes.status} body=${loginRes.body?.slice(0, 200)}`);
  }

  sleep(1);
}

// ============================================================
// סיכום בסוף הריצה
// ============================================================
export function handleSummary(data) {
  const dur_reg = data.metrics["register_duration"];
  const dur_login = data.metrics["login_duration"];
  const failed = data.metrics["http_req_failed"];

  console.log("\n=== LINKUP LOAD TEST SUMMARY ===");
  if (dur_reg) {
    console.log(`/register p95: ${dur_reg.values["p(95)"]?.toFixed(0)}ms`);
  }
  if (dur_login) {
    console.log(`/login    p95: ${dur_login.values["p(95)"]?.toFixed(0)}ms`);
  }
  if (failed) {
    const rate = (failed.values.rate * 100).toFixed(2);
    console.log(
      `Error rate: ${rate}% ${failed.values.rate < 0.05 ? "✅" : "❌"}`
    );
  }
  return {};
}
