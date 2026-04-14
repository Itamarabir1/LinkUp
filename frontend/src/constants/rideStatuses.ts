/**
 * Ride statuses that require real-time WebSocket updates.
 * Single source of truth — used by MyRides and useMyBookingsPassenger.
 */
export const LIVE_STATUSES = new Set(['open', 'full', 'active']);
