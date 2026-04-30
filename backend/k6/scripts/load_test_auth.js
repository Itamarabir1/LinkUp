import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";
import { BASE_URL, HEADERS, jsonOrNull } from "../lib/helpers.js";
import { buildOptions } from "../lib/options.js";

const loginDuration = new Trend("auth_login_duration", true);
const rateLimitTriggered = new Rate("auth_rate_limit_triggered");
const rateLimitHeaderErrors = new Rate("auth_rate_limit_header_errors");
const status429Count = new Counter("auth_rate_limit_429_total");

const thresholds = {
  auth_login_duration: ["p(95)<1500"],
  auth_rate_limit_triggered: ["rate>0.95"],
  auth_rate_limit_header_errors: ["rate<0.05"],
};

export const options = buildOptions(thresholds, [
  { duration: "20s", target: 5 },
  { duration: "20s", target: 10 },
  { duration: "20s", target: 0 },
]);

function loginPayload() {
  return JSON.stringify({
    email: __ENV.USER_EMAIL,
    password: __ENV.USER_PASSWORD,
  });
}

export function setup() {
  if (!__ENV.USER_EMAIL || !__ENV.USER_PASSWORD) {
    throw new Error("Missing USER_EMAIL / USER_PASSWORD for auth rate-limit test");
  }

  const warmupRes = http.post(`${BASE_URL}/auth/login`, loginPayload(), { headers: HEADERS });
  const warmupBody = jsonOrNull(warmupRes);
  if (warmupRes.status !== 200 || !warmupBody?.access_token) {
    throw new Error(`setup login failed: status=${warmupRes.status} body=${warmupRes.body?.slice(0, 300)}`);
  }
}

export default function () {
  const burst = parseInt(__ENV.RATE_LIMIT_BURST || "20", 10);
  let saw429 = false;

  for (let i = 0; i < burst; i++) {
    const res = http.post(`${BASE_URL}/auth/login`, loginPayload(), { headers: HEADERS });
    loginDuration.add(res.timings.duration);

    if (res.status === 429) {
      saw429 = true;
      status429Count.add(1);
      const retryAfter = res.headers["Retry-After"];
      const rateLimitLimit = res.headers["X-Ratelimit-Limit"];
      const rateLimitRemaining = res.headers["X-Ratelimit-Remaining"];
      const hasHeaders =
        typeof retryAfter === "string" &&
        retryAfter.length > 0 &&
        typeof rateLimitLimit === "string" &&
        rateLimitLimit.length > 0 &&
        typeof rateLimitRemaining === "string" &&
        rateLimitRemaining.length > 0;
      rateLimitHeaderErrors.add(!hasHeaders);
      continue;
    }

    // Before the limiter kicks in, valid existing credentials should still login successfully.
    const okBeforeLimit = check(res, {
      "auth login status 200 before limit": (r) => r.status === 200,
    });
    if (!okBeforeLimit) {
      rateLimitHeaderErrors.add(true);
    }
  }

  rateLimitTriggered.add(saw429);
  check({ saw429 }, {
    "rate limiting eventually returns 429": (o) => o.saw429,
  });
  sleep(1);
}
