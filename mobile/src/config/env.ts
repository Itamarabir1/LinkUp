/**
 * Base URL of the LinkUp backend API.
 * Android emulator: use 10.0.2.2 for localhost.
 * Physical device: use your machine IP (e.g. 192.168.1.x).
 */
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL || 'http://10.0.2.2:8000/api/v1';

export const WS_BASE_URL =
  process.env.EXPO_PUBLIC_WS_URL || 'ws://10.0.2.2:8000/api/v1';
