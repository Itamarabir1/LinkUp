import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { BASE_URL, HEADERS, uniqueUser, jsonOrNull } from "../lib/helpers.js";
import { buildOptions } from "../lib/options.js";

const registerErrors = new Rate("register_errors");
const loginErrors = new Rate("login_errors");
const registerDuration = new Trend("register_duration", true);
const loginDuration = new Trend("login_duration", true);

const thresholds = {
  register_errors: ["rate<0.05"],
  login_errors: ["rate<0.05"],
  register_duration: ["p(95)<3000"],
  login_duration: ["p(95)<1500"],
  http_req_failed: ["rate<0.05"],
};

export const options = buildOptions(thresholds, [
  { duration: "30s", target: 50 },
  { duration: "1m", target: 200 },
  { duration: "1m", target: 500 },
  { duration: "30s", target: 0 },
]);

export default function () {
  const user = uniqueUser("auth");
  const registerRes = http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify(user),
    { headers: HEADERS }
  );
  registerDuration.add(registerRes.timings.duration);

  const registerBody = jsonOrNull(registerRes);
  const registerOk = check(registerRes, {
    "register status 201": (r) => r.status === 201,
    "register has user_id": () => !!registerBody?.user_id,
  });
  registerErrors.add(!registerOk);
  if (!registerOk) {
    console.error(`[register FAIL] status=${registerRes.status} body=${registerRes.body?.slice(0, 200)}`);
    sleep(1);
    return;
  }

  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    { headers: HEADERS }
  );
  loginDuration.add(loginRes.timings.duration);
  const loginBody = jsonOrNull(loginRes);
  const loginOk = check(loginRes, {
    "login status 200": (r) => r.status === 200,
    "login has access_token": () => !!loginBody?.access_token,
    "login has refresh_token": () => !!loginBody?.refresh_token,
  });
  loginErrors.add(!loginOk);
  if (!loginOk) {
    console.error(`[login FAIL] status=${loginRes.status} body=${loginRes.body?.slice(0, 200)}`);
  }
  sleep(1);
}

export function handleSummary(data) {
  const m = data.metrics;
  const VUS = parseInt(__ENV.VUS) || null;
  const DURATION = __ENV.DURATION || null;
  console.log("\n=== AUTH LOAD TEST SUMMARY ===");
  console.log(
    VUS && DURATION ? `Mode: Manual — VUs=${VUS}, Duration=${DURATION}` : "Mode: Stages — full ramp-up test"
  );
  if (m.register_duration) console.log(`/register p95: ${m.register_duration.values["p(95)"]?.toFixed(0)}ms`);
  if (m.login_duration) console.log(`/login    p95: ${m.login_duration.values["p(95)"]?.toFixed(0)}ms`);
  if (m.http_req_failed) {
    const rate = (m.http_req_failed.values.rate * 100).toFixed(2);
    console.log(`Error rate: ${rate}% ${m.http_req_failed.values.rate < 0.05 ? "✓ OK" : "✗ HIGH"}`);
  }
  return {};
}
