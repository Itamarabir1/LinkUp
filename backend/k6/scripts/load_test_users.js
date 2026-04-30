import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { BASE_URL, loginExisting, jsonOrNull } from "../lib/helpers.js";
import { buildOptions } from "../lib/options.js";

const meErrors = new Rate("users_me_errors");
const updateErrors = new Rate("users_update_errors");
const avatarErrors = new Rate("users_avatar_errors");
const publicErrors = new Rate("users_public_errors");

const meDuration = new Trend("users_me_duration", true);
const updateDuration = new Trend("users_update_duration", true);
const avatarDuration = new Trend("users_avatar_duration", true);
const publicDuration = new Trend("users_public_duration", true);

const thresholds = {
  users_me_errors: ["rate<0.05"],
  users_update_errors: ["rate<0.10"],
  users_avatar_errors: ["rate<0.20"],
  users_public_errors: ["rate<0.30"],
  users_me_duration: ["p(95)<1500"],
  users_update_duration: ["p(95)<2000"],
  users_avatar_duration: ["p(95)<2500"],
  users_public_duration: ["p(95)<1500"],
};

export const options = buildOptions(thresholds, [
  { duration: "30s", target: 10 },
  { duration: "1m", target: 20 },
  { duration: "30s", target: 0 },
]);

export function setup() {
  const session = loginExisting(__ENV.USER_EMAIL, __ENV.USER_PASSWORD);
  if (!session.ok) {
    throw new Error(`setup login failed: session_ok=${session.ok}`);
  }
  return {
    userId: session.userId,
    token: session.token,
    authHeaders: session.authHeaders,
  };
}

export default function (data) {
  const session = data;

  const meRes = http.get(`${BASE_URL}/users/me`, { headers: session.authHeaders });
  meDuration.add(meRes.timings.duration);
  const meBody = jsonOrNull(meRes);
  const meOk = check(meRes, { "users/me status 200": (r) => r.status === 200 });
  meErrors.add(!meOk);
  if (!meOk) return;

  const updateRes = http.put(
    `${BASE_URL}/users/me`,
    JSON.stringify({
      full_name: `Updated ${Date.now()}`,
      phone_number: meBody?.phone_number,
      email: meBody?.email,
    }),
    { headers: session.authHeaders }
  );
  updateDuration.add(updateRes.timings.duration);
  const updateOk = check(updateRes, { "users/me update status 200": (r) => r.status === 200 });
  updateErrors.add(!updateOk);

  const uploadUrlRes = http.get(`${BASE_URL}/users/me/avatar/upload-url?filename=test.jpg`, {
    headers: session.authHeaders,
  });
  avatarDuration.add(uploadUrlRes.timings.duration);
  const uploadBody = jsonOrNull(uploadUrlRes);
  const uploadOk = check(uploadUrlRes, {
    "avatar upload-url status 200": (r) => r.status === 200,
    "avatar upload-url has staging_key": () => !!uploadBody?.staging_key,
  });
  avatarErrors.add(!uploadOk);

  if (uploadOk) {
    const confirmRes = http.post(
      `${BASE_URL}/users/me/avatar/confirm`,
      JSON.stringify({ staging_key: uploadBody.staging_key }),
      { headers: session.authHeaders }
    );
    avatarDuration.add(confirmRes.timings.duration);
    const confirmOk = check(confirmRes, {
      "avatar confirm status 202 or 503": (r) => r.status === 202 || r.status === 503,
    });
    avatarErrors.add(!confirmOk);
  }

  const publicPath = (__ENV.USER_PUBLIC_PATH || "/users/{id}").replace("{id}", session.userId);
  const publicRes = http.get(`${BASE_URL}${publicPath}`, { headers: session.authHeaders });
  publicDuration.add(publicRes.timings.duration);
  // In this codebase /users/{id} may be disabled; accept 404 but keep measured.
  const publicOk = check(publicRes, {
    "user public endpoint reachable": (r) => [200, 404].includes(r.status),
  });
  publicErrors.add(!publicOk);

  sleep(1);
}
