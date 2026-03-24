import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { BASE_URL, registerAndLogin, jsonOrNull } from "../lib/helpers.js";

const mapsKeyErrors = new Rate("geo_maps_key_errors");
const reverseErrors = new Rate("geo_reverse_errors");
const geocodeErrors = new Rate("geo_geocode_errors");
const distanceErrors = new Rate("geo_distance_errors");

const mapsKeyDuration = new Trend("geo_maps_key_duration", true);
const reverseDuration = new Trend("geo_reverse_duration", true);
const geocodeDuration = new Trend("geo_geocode_duration", true);
const distanceDuration = new Trend("geo_distance_duration", true);

export const options = {
  thresholds: {
    geo_maps_key_errors: ["rate<0.10"],
    geo_reverse_errors: ["rate<0.20"],
    geo_geocode_errors: ["rate<0.25"],
    geo_distance_errors: ["rate<0.25"],
    geo_maps_key_duration: ["p(95)<1500"],
    geo_reverse_duration: ["p(95)<3000"],
    geo_geocode_duration: ["p(95)<3500"],
    geo_distance_duration: ["p(95)<3500"],
  },
};

export default function () {
  const session = registerAndLogin("geo");
  if (!session.ok) return;

  const mapsKeyRes = http.get(`${BASE_URL}/geo/maps-key`, { headers: session.authHeaders });
  mapsKeyDuration.add(mapsKeyRes.timings.duration);
  const mapsKeyBody = jsonOrNull(mapsKeyRes);
  const mapsKeyOk = check(mapsKeyRes, {
    "geo maps-key status 200": (r) => r.status === 200,
    "geo maps-key payload": () => typeof mapsKeyBody?.google_maps_api_key === "string",
  });
  mapsKeyErrors.add(!mapsKeyOk);

  const reverseRes = http.get(`${BASE_URL}/geo/address?lat=32.0853&lon=34.7818`, {
    headers: session.authHeaders,
  });
  reverseDuration.add(reverseRes.timings.duration);
  const reverseOk = check(reverseRes, {
    "geo reverse status 200": (r) => r.status === 200,
  });
  reverseErrors.add(!reverseOk);

  // There is no dedicated /geo/geocode endpoint in this backend.
  // Simulate geocoding pressure via passenger search, which performs address->coords.
  const geocodeRes = http.get(
    `${BASE_URL}/passenger/passengers/search-rides?pickup_name=${encodeURIComponent("תל אביב")}&destination_name=${encodeURIComponent("ירושלים")}&search_radius=5000&limit=5`,
    { headers: session.authHeaders }
  );
  geocodeDuration.add(geocodeRes.timings.duration);
  const geocodeOk = check(geocodeRes, {
    "geo geocode-via-search status 200": (r) => r.status === 200,
  });
  geocodeErrors.add(!geocodeOk);

  // There is no exposed distance-matrix endpoint; route preview triggers routing/distance calculations.
  const distanceRes = http.post(
    `${BASE_URL}/rides/preview-routes`,
    JSON.stringify({
      driver_id: session.userId,
      origin_lat: 32.0853,
      origin_lon: 34.7818,
      destination_name: "ירושלים, ישראל",
      departure_time: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
      available_seats: 3,
      price: 30,
    }),
    { headers: session.authHeaders }
  );
  distanceDuration.add(distanceRes.timings.duration);
  const distanceOk = check(distanceRes, {
    "geo distance-via-preview status 200": (r) => r.status === 200,
  });
  distanceErrors.add(!distanceOk);

  sleep(1);
}
