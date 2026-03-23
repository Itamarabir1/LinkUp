import { api } from './client';

export function fetchAddressFromCoords(lat: number, lon: number) {
  return api.get<{ address: string }>('/geo/address', { params: { lat, lon } });
}

export function fetchMapsKey() {
  return api.get<{ google_maps_api_key: string }>('/geo/maps-key');
}
