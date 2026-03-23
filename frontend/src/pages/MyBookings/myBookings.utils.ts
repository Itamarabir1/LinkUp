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
