import type { Ride } from '../../types/api';
import { getRideSourceLabel, type GroupNameRef } from '../../utils/rideDisplay';

export const canPassengerShare = (bookingStatus: string, rideStatus: string) =>
  bookingStatus === 'confirmed' && rideStatus === 'active';

export const canDriverShare = (confirmedCount: number) => confirmedCount >= 1;

export const canDriverOpenMap = (confirmedCount: number) => confirmedCount >= 1;

export function getSource(ride: Ride, myGroups: GroupNameRef[]): string {
  return getRideSourceLabel(ride.group_id, myGroups);
}

export function avatarInitial(name: string): string {
  return (name || 'נ').charAt(0).toUpperCase();
}

type PickupDropoffTranslate = (key: 'bookings:pickup' | 'bookings:dropoff') => string;

/** Pickup/dropoff line for driver passenger rows (presentational only). */
export function formatPickupDropoffLine(
  pickup: string | null | undefined,
  dropoff: string | null | undefined,
  t: PickupDropoffTranslate
): string {
  const parts = [
    pickup ? `${t('bookings:pickup')}: ${pickup}` : '',
    dropoff ? `${t('bookings:dropoff')}: ${dropoff}` : '',
  ].filter(Boolean);
  return parts.join(' · ');
}
