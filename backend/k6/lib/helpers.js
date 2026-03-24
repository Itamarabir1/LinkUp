import http from "k6/http";

export const BASE_URL = __ENV.BASE_URL || "http://localhost:8000/api/v1";
export const HEADERS = { "Content-Type": "application/json" };

let userCounter = 0;

export function uniquePhone() {
  userCounter++;
  const suffix = String(8000000 + __VU * 10000 + userCounter).padStart(7, "0");
  return `+97250${suffix}`;
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
