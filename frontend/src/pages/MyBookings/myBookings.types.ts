import type { Ride } from '../../types/api';

export interface BookingRow {
  booking_id: string;
  ride_id: string;
  request_id: string;
  passenger_id: string;
  num_seats: number;
  status: string;
  created_at?: string;
  passenger_name?: string;
  phone?: string;
}

/** Passenger-side bookings: booking + ride details + driver name. */
export interface PassengerBookingItem {
  ride: Ride;
  bookingId: string;
  bookingStatus: string;
  driverName: string | null;
}

/** Passenger item within one of my rides (driver view). */
export interface PassengerInRide {
  bookingId: string;
  passengerName: string;
  numSeats: number;
  status: string;
  pickupName?: string | null;
  pickupTime?: string | null;
  /** Passenger-request destination (from passenger_request). */
  dropoffName?: string | null;
}

/** Driver-side bookings: ride with all attached passengers. */
export interface DriverBookingItem {
  ride: Ride;
  passengers: PassengerInRide[];
}

export type TabKind = 'driver' | 'passenger';
