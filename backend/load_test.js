// k6 load test — auth register + login
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

// יוצר משתמש ייחודי לכל iteration (כדי לא לפגוע ב-unique constraint)
function uniqueUser() {
  const id = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  return {
    full_name: `Test User ${id}`,
    email: `test_${id}@loadtest.com`,
    phone_number: `+9725${Math.floor(10000000 + Math.random() * 89999999)}`,
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
  const r = data.metrics;

  const summary = {
    register: {
      total:    r.http_reqs?.values?.count ?? 0,
      errors:   `${((r.register_errors?.values?.rate ?? 0) * 100).toFixed(1)}%`,
      p95_ms:   r.register_duration?.values?.["p(95)"] ?? 0,
    },
    login: {
      errors:   `${((r.login_errors?.values?.rate ?? 0) * 100).toFixed(1)}%`,
      p95_ms:   r.login_duration?.values?.["p(95)"] ?? 0,
    },
    thresholds_passed: !data.rootGroup.checks?.some?.(c => !c.passes),
  };

  console.log("\n===== תוצאות Load Test =====");
  console.log(JSON.stringify(summary, null, 2));
  console.log("============================\n");

  return {
    "load_test_summary.json": JSON.stringify(summary, null, 2),
  };
}
