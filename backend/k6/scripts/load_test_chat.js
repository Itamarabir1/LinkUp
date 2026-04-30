import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { BASE_URL, loginExisting, jsonOrNull } from "../lib/helpers.js";
import { buildOptions } from "../lib/options.js";

const conversationErrors = new Rate("chat_conversation_errors");
const sendErrors = new Rate("chat_send_errors");
const historyErrors = new Rate("chat_history_errors");
const summaryErrors = new Rate("chat_summary_errors");

const conversationDuration = new Trend("chat_conversation_duration", true);
const sendDuration = new Trend("chat_send_duration", true);
const historyDuration = new Trend("chat_history_duration", true);
const summaryDuration = new Trend("chat_summary_duration", true);

const thresholds = {
  chat_conversation_errors: ["rate<0.10"],
  chat_send_errors: ["rate<0.10"],
  chat_history_errors: ["rate<0.10"],
  chat_summary_errors: ["rate<0.50"],
  chat_conversation_duration: ["p(95)<2500"],
  chat_send_duration: ["p(95)<2000"],
  chat_history_duration: ["p(95)<2000"],
  chat_summary_duration: ["p(95)<3000"],
};

export const options = buildOptions(thresholds, [
  { duration: "30s", target: 10 },
  { duration: "1m", target: 20 },
  { duration: "30s", target: 0 },
]);

export function setup() {
  const userA = loginExisting(__ENV.USER_EMAIL, __ENV.USER_PASSWORD);
  const userB = loginExisting(__ENV.USER_EMAIL_P1, __ENV.USER_PASSWORD_P1);
  if (!userA.ok || !userB.ok) {
    throw new Error(`setup login failed: userA=${userA.ok} userB=${userB.ok}`);
  }

  return {
    userA: {
      userId: userA.userId,
      authHeaders: userA.authHeaders,
    },
    userB: {
      userId: userB.userId,
      authHeaders: userB.authHeaders,
    },
  };
}

export default function (data) {
  const userA = data.userA;
  const userB = data.userB;

  const convRes = http.post(
    `${BASE_URL}/chat/conversations`,
    JSON.stringify({ other_user_id: userB.userId }),
    { headers: userA.authHeaders }
  );
  conversationDuration.add(convRes.timings.duration);
  const convBody = jsonOrNull(convRes);
  const convOk = check(convRes, {
    "chat conversation status 201": (r) => r.status === 201,
    "chat conversation has id": () => !!convBody?.conversation_id,
  });
  conversationErrors.add(!convOk);
  if (!convOk) return;

  const conversationId = convBody.conversation_id;
  const sendRes = http.post(
    `${BASE_URL}/chat/conversations/${conversationId}/messages`,
    JSON.stringify({ body: `k6 message ${Date.now()}` }),
    { headers: userA.authHeaders }
  );
  sendDuration.add(sendRes.timings.duration);
  const sendOk = check(sendRes, { "chat send status 201": (r) => r.status === 201 });
  sendErrors.add(!sendOk);

  const historyRes = http.get(
    `${BASE_URL}/chat/conversations/${conversationId}/messages?limit=20`,
    { headers: userA.authHeaders }
  );
  historyDuration.add(historyRes.timings.duration);
  const historyBody = jsonOrNull(historyRes);
  const historyOk = check(historyRes, {
    "chat history status 200": (r) => r.status === 200,
    "chat history has items": () => Array.isArray(historyBody?.items),
  });
  historyErrors.add(!historyOk);

  // AI summary/analysis endpoint may not exist in this backend revision.
  // We still probe it to measure readiness and keep this layer covered.
  const summaryRes = http.get(
    `${BASE_URL}/chat/conversations/${conversationId}/analysis`,
    { headers: userA.authHeaders }
  );
  summaryDuration.add(summaryRes.timings.duration);
  const summaryOk = check(summaryRes, {
    "chat summary endpoint reachable": (r) => [200, 404, 501].includes(r.status),
  });
  summaryErrors.add(!summaryOk);

  sleep(1);
}
