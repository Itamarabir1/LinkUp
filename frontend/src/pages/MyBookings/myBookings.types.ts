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

/** הזמנות שבהן אני נוסע – מבוקינג + פרטי נסיעה + שם נהג */
export interface PassengerBookingItem {
  ride: Ride;
  bookingId: string;
  bookingStatus: string;
  driverName: string | null;
}

/** נוסע בנסיעה שלי (כנהג) */
export interface PassengerInRide {
  bookingId: string;
  passengerName: string;
  numSeats: number;
  status: string;
  pickupName?: string | null;
  pickupTime?: string | null;
  /** יעד הבקשה של הנוסע (מ-passenger_request) */
  dropoffName?: string | null;
}

/** הזמנות שבהן אני נהג – נסיעה עם כל הנוסעים שלה */
export interface DriverBookingItem {
  ride: Ride;
  passengers: PassengerInRide[];
}

export type TabKind = 'driver' | 'passenger';
