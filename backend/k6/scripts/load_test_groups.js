import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { BASE_URL, registerAndLogin, jsonOrNull } from "../lib/helpers.js";

const createErrors = new Rate("groups_create_errors");
const joinErrors = new Rate("groups_join_errors");
const membersErrors = new Rate("groups_members_errors");
const leaveErrors = new Rate("groups_leave_errors");

const createDuration = new Trend("groups_create_duration", true);
const joinDuration = new Trend("groups_join_duration", true);
const membersDuration = new Trend("groups_members_duration", true);
const leaveDuration = new Trend("groups_leave_duration", true);

export const options = {
  thresholds: {
    groups_create_errors: ["rate<0.10"],
    groups_join_errors: ["rate<0.10"],
    groups_members_errors: ["rate<0.10"],
    groups_leave_errors: ["rate<0.10"],
    groups_create_duration: ["p(95)<2500"],
    groups_join_duration: ["p(95)<2500"],
    groups_members_duration: ["p(95)<2000"],
    groups_leave_duration: ["p(95)<2000"],
  },
};

export default function () {
  const owner = registerAndLogin("group_owner");
  const member = registerAndLogin("group_member");
  if (!owner.ok || !member.ok) return;

  const createRes = http.post(
    `${BASE_URL}/groups`,
    JSON.stringify({
      name: `k6-group-${__VU}-${__ITER}-${Date.now()}`,
      description: "k6 load test group",
    }),
    { headers: owner.authHeaders }
  );
  createDuration.add(createRes.timings.duration);
  const createBody = jsonOrNull(createRes);
  const createOk = check(createRes, {
    "group create status 201": (r) => r.status === 201,
    "group create has id": () => !!createBody?.group_id,
    "group create has invite": () => !!createBody?.invite_code,
  });
  createErrors.add(!createOk);
  if (!createOk) return;

  const inviteCode = createBody.invite_code;
  const groupId = createBody.group_id;

  const joinRes = http.post(`${BASE_URL}/groups/join/${inviteCode}`, null, {
    headers: member.authHeaders,
  });
  joinDuration.add(joinRes.timings.duration);
  const joinOk = check(joinRes, {
    "group join status 200": (r) => r.status === 200,
  });
  joinErrors.add(!joinOk);
  if (!joinOk) return;

  const membersRes = http.get(`${BASE_URL}/groups/${groupId}/members`, {
    headers: owner.authHeaders,
  });
  membersDuration.add(membersRes.timings.duration);
  const membersBody = jsonOrNull(membersRes);
  const membersOk = check(membersRes, {
    "group members status 200": (r) => r.status === 200,
    "group members list": () => Array.isArray(membersBody),
  });
  membersErrors.add(!membersOk);

  const leaveRes = http.del(`${BASE_URL}/groups/${groupId}/leave`, null, {
    headers: member.authHeaders,
  });
  leaveDuration.add(leaveRes.timings.duration);
  const leaveOk = check(leaveRes, {
    "group leave status 204": (r) => r.status === 204,
  });
  leaveErrors.add(!leaveOk);

  sleep(1);
}
