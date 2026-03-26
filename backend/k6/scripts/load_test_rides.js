import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { BASE_URL, registerAndLogin, jsonOrNull } from "../lib/helpers.js";
import { buildOptions } from "../lib/options.js";

const previewErrors = new Rate("preview_errors");
const createErrors = new Rate("create_errors");
const searchErrors = new Rate("search_errors");
const joinErrors = new Rate("join_errors");
const approveErrors = new Rate("approve_errors");
const rejectErrors = new Rate("reject_errors");
const cancelRideErrors = new Rate("cancel_ride_errors");

const previewDuration = new Trend("preview_duration", true);
const createDuration = new Trend("create_duration", true);
const searchDuration = new Trend("search_duration", true);
const joinDuration = new Trend("join_duration", true);
const approveDuration = new Trend("approve_duration", true);
const rejectDuration = new Trend("reject_duration", true);
const cancelRideDuration = new Trend("cancel_ride_duration", true);

const thresholds = {
  preview_duration: ["p(95)<3000"],
  create_duration: ["p(95)<3000"],
  search_duration: ["p(95)<5000"],
  join_duration: ["p(95)<3000"],
  approve_duration: ["p(95)<3000"],
  reject_duration: ["p(95)<3000"],
  cancel_ride_duration: ["p(95)<3000"],
  preview_errors: ["rate<0.05"],
  create_errors: ["rate<0.05"],
  search_errors: ["rate<0.10"],
  join_errors: ["rate<0.10"],
  approve_errors: ["rate<0.10"],
  reject_errors: ["rate<0.10"],
  cancel_ride_errors: ["rate<0.10"],
};

export const options = buildOptions(thresholds, [
  { duration: "30s", target: 10 },
  { duration: "1m", target: 20 },
  { duration: "30s", target: 0 },
]);

const ORIGIN = { lat: 32.0853, lon: 34.7818, name: "Tel Aviv, Israel" };
const DESTINATION = { lat: 31.7683, lon: 35.2137, name: "Jerusalem, Israel" };

function departureTime() {
  return new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
}

export default function () {
  const driver = registerAndLogin("driver");
  if (!driver.ok) return;

  const previewRes = http.post(
    `${BASE_URL}/rides/preview-routes`,
    JSON.stringify({
      driver_id: driver.userId,
      origin_lat: ORIGIN.lat,
      origin_lon: ORIGIN.lon,
      destination_name: DESTINATION.name,
      departure_time: departureTime(),
      available_seats: 3,
      price: 25.0,
    }),
    { headers: driver.authHeaders }
  );
  previewDuration.add(previewRes.timings.duration);
  const previewBody = jsonOrNull(previewRes);
  const previewOk = check(previewRes, {
    "preview status 200": (r) => r.status === 200,
    "preview has session_id": () => !!previewBody?.session_id,
  });
  previewErrors.add(!previewOk);
  if (!previewOk) return;

  const createRes = http.post(
    `${BASE_URL}/rides/`,
    JSON.stringify({ session_id: previewBody.session_id, selected_route_index: 0 }),
    { headers: driver.authHeaders }
  );
  createDuration.add(createRes.timings.duration);
  const createBody = jsonOrNull(createRes);
  const createOk = check(createRes, {
    "create status 201": (r) => r.status === 201,
    "create has ride_id": () => !!createBody?.ride_id,
  });
  createErrors.add(!createOk);
  if (!createOk) return;

  const rideId = createBody.ride_id;
  const passenger1 = registerAndLogin("p1");
  if (!passenger1.ok) return;

  const searchRes = http.get(
    `${BASE_URL}/passenger/passengers/search-rides?pickup_name=${encodeURIComponent("Tel Aviv")}&destination_name=${encodeURIComponent("Jerusalem")}&search_radius=5000&limit=10`,
    { headers: passenger1.authHeaders }
  );
  searchDuration.add(searchRes.timings.duration);
  const searchBody = jsonOrNull(searchRes);
  const searchOk = check(searchRes, {
    "search status 200": (r) => r.status === 200,
    "search has items": () => Array.isArray(searchBody?.items),
  });
  searchErrors.add(!searchOk);
  if (!searchOk) return;

  const req1 = http.post(
    `${BASE_URL}/passenger/passengers/`,
    JSON.stringify({
      num_passengers: 1,
      pickup_name: ORIGIN.name,
      destination_name: DESTINATION.name,
      requested_departure_time: departureTime(),
      search_radius: 5000,
      is_notification_active: true,
      pickup_lat: ORIGIN.lat,
      pickup_lon: ORIGIN.lon,
    }),
    { headers: passenger1.authHeaders }
  );
  const req1Body = jsonOrNull(req1);
  if (req1.status !== 201 || !req1Body?.request_id) return;

  const join1 = http.post(
    `${BASE_URL}/bookings/request-to-join`,
    JSON.stringify({ ride_id: rideId, request_id: req1Body.request_id, num_seats: 1 }),
    { headers: passenger1.authHeaders }
  );
  joinDuration.add(join1.timings.duration);
  const join1Body = jsonOrNull(join1);
  const join1Ok = check(join1, { "join #1 status 201": (r) => r.status === 201 });
  joinErrors.add(!join1Ok);
  if (!join1Ok || !join1Body?.booking_id) return;

  const approve = http.patch(
    `${BASE_URL}/bookings/${join1Body.booking_id}/approve?driver_id=${driver.userId}`,
    null,
    { headers: driver.authHeaders }
  );
  approveDuration.add(approve.timings.duration);
  const approveBody = jsonOrNull(approve);
  const approveOk = check(approve, {
    "approve status 200": (r) => r.status === 200,
    "approve confirmed": () => approveBody?.status === "confirmed",
  });
  approveErrors.add(!approveOk);
  if (!approveOk) return;

  const passenger2 = registerAndLogin("p2");
  if (!passenger2.ok) return;
  const req2 = http.post(
    `${BASE_URL}/passenger/passengers/`,
    JSON.stringify({
      num_passengers: 1,
      pickup_name: ORIGIN.name,
      destination_name: DESTINATION.name,
      requested_departure_time: departureTime(),
      search_radius: 5000,
      is_notification_active: true,
      pickup_lat: ORIGIN.lat,
      pickup_lon: ORIGIN.lon,
    }),
    { headers: passenger2.authHeaders }
  );
  const req2Body = jsonOrNull(req2);
  if (req2.status !== 201 || !req2Body?.request_id) return;

  const join2 = http.post(
    `${BASE_URL}/bookings/request-to-join`,
    JSON.stringify({ ride_id: rideId, request_id: req2Body.request_id, num_seats: 1 }),
    { headers: passenger2.authHeaders }
  );
  const join2Body = jsonOrNull(join2);
  const join2Ok = check(join2, { "join #2 status 201": (r) => r.status === 201 });
  joinErrors.add(!join2Ok);
  if (!join2Ok || !join2Body?.booking_id) return;

  const reject = http.patch(
    `${BASE_URL}/bookings/${join2Body.booking_id}/reject?driver_id=${driver.userId}`,
    null,
    { headers: driver.authHeaders }
  );
  rejectDuration.add(reject.timings.duration);
  const rejectBody = jsonOrNull(reject);
  const rejectOk = check(reject, {
    "reject status 200": (r) => r.status === 200,
    "reject rejected": () => rejectBody?.status === "rejected",
  });
  rejectErrors.add(!rejectOk);
  if (!rejectOk) return;

  const cancelRes = http.del(`${BASE_URL}/rides/${rideId}/cancel`, null, {
    headers: driver.authHeaders,
  });
  cancelRideDuration.add(cancelRes.timings.duration);
  const cancelOk = check(cancelRes, { "cancel ride status 204": (r) => r.status === 204 });
  cancelRideErrors.add(!cancelOk);

  sleep(1);
}
