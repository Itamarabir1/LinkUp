import http from "k6/http";

export const BASE_URL = __ENV.BASE_URL || "http://localhost:8000/api/v1";
export const HEADERS = { "Content-Type": "application/json" };

let userCounter = 0;
// Per-run salt so repeat k6 runs don't collide with DB rows from earlier runs.
const BASE_TS = Date.now() % 10000000;

export function uniquePhone() {
  userCounter++;
  // Two trusted IL E.164 blocks: +972534XXXXXX and +972544XXXXXX (6-digit suffix each); BASE_TS/VU spread across runs.
  const suffix = String((BASE_TS + __VU * 10000 + userCounter) % 1000000).padStart(6, "0");
  const prefix = userCounter % 2 === 0 ? "534" : "544";
  return `+972${prefix}${suffix}`;
}

export function uniqueUser(role = "user") {
  const unique = `${role}_${__VU}_${__ITER}_${Date.now()}_${Math.random()
    .toString(36)
    .slice(2, 7)}`;
  return {
    full_name: `Load ${role}`,
    email: `${unique}@loadtest.linkup.co.il`,
    phone_number: uniquePhone(),
    password: "TestPass123!",
    confirm_password: "TestPass123!",
  };
}

export function registerAndLogin(role = "user") {
  const user = uniqueUser(role);
  const registerRes = http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify(user),
    { headers: HEADERS }
  );
  if (registerRes.status !== 201) {
    return { ok: false, step: "register", response: registerRes, user };
  }

  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    { headers: HEADERS }
  );
  if (loginRes.status !== 200) {
    return { ok: false, step: "login", response: loginRes, user };
  }

  let payload;
  try {
    payload = JSON.parse(loginRes.body);
  } catch {
    return { ok: false, step: "login_parse", response: loginRes, user };
  }

  if (!payload.access_token || !payload.user?.user_id) {
    return { ok: false, step: "login_payload", response: loginRes, user };
  }

  return {
    ok: true,
    user,
    token: payload.access_token,
    userId: payload.user.user_id,
    authHeaders: { ...HEADERS, Authorization: `Bearer ${payload.access_token}` },
    registerRes,
    loginRes,
  };
}

export function jsonOrNull(response) {
  try {
    return JSON.parse(response.body);
  } catch {
    return null;
  }
}
