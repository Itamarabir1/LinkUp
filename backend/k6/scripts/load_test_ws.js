import http from "k6/http";
import ws from "k6/ws";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";
import { BASE_URL, registerAndLogin } from "../lib/helpers.js";
import { buildOptions } from "../lib/options.js";

const wsConnectErrors = new Rate("ws_connect_errors");
const wsMessageErrors = new Rate("ws_message_errors");
const wsConnectDuration = new Trend("ws_connect_duration", true);
const wsMessages = new Counter("ws_messages_total");

const thresholds = {
  ws_connect_errors: ["rate<0.15"],
  ws_message_errors: ["rate<0.25"],
  ws_connect_duration: ["p(95)<3000"],
};

export const options = buildOptions(thresholds, [
  { duration: "30s", target: 10 },
  { duration: "1m", target: 20 },
  { duration: "30s", target: 0 },
]);

function baseHost() {
  const configured = __ENV.WS_URL || "ws://localhost:8081/ws";
  return configured;
}

export default function () {
  const session = registerAndLogin("ws");
  if (!session.ok) return;

  // 1) chat-ws channel
  const chatStart = Date.now();
  const chatUrl = `${baseHost()}?token=${session.token}`;
  const chatRes = ws.connect(chatUrl, null, function (socket) {
    let gotAnyMessage = false;

    socket.on("open", () => {
      // passive connect; chat messages come from backend->redis->chat-ws pipeline
      socket.setTimeout(() => socket.close(), 3000);
    });

    socket.on("message", () => {
      gotAnyMessage = true;
      wsMessages.add(1);
    });

    socket.on("close", () => {
      // no-op
    });

    socket.on("error", () => {
      wsMessageErrors.add(true);
    });

    socket.setTimeout(() => {
      if (!gotAnyMessage) {
        // acceptable for short windows, but tracked
        wsMessageErrors.add(false);
      }
      socket.close();
    }, 2500);
  });
  wsConnectDuration.add(Date.now() - chatStart);
  const chatOk = check(chatRes, {
    "chat ws connect status 101": (r) => r && r.status === 101,
  });
  wsConnectErrors.add(!chatOk);

  // 2) backend notifications websocket
  const notifyBase = (__ENV.NOTIFY_WS_URL || "ws://localhost:8000/api/v1/notifications/ws");
  const notifyUrl = `${notifyBase}?token=${session.token}`;
  const notifyStart = Date.now();
  const notifyRes = ws.connect(notifyUrl, null, function (socket) {
    socket.on("open", () => {
      socket.setTimeout(() => socket.close(), 2000);
    });
    socket.on("message", () => {
      wsMessages.add(1);
    });
    socket.on("error", () => {
      wsMessageErrors.add(true);
    });
  });
  wsConnectDuration.add(Date.now() - notifyStart);
  const notifyOk = check(notifyRes, {
    "notify ws connect status 101": (r) => r && r.status === 101,
  });
  wsConnectErrors.add(!notifyOk);

  // 3) presence HTTP check from chat-ws (side endpoint related to realtime stack)
  const presenceBase = __ENV.PRESENCE_URL || "http://localhost:8081/presence";
  const presenceRes = http.get(`${presenceBase}/${session.userId}`, {
    headers: { Authorization: `Bearer ${session.token}` },
  });
  check(presenceRes, {
    "presence status 200": (r) => r.status === 200,
  });

  sleep(1);
}
