import type {
  DriverBookingItem,
  PassengerBookingItem,
  PassengerInRide,
} from './myBookings.types';
import type {
  DriverActiveResponse,
  PassengerBookingSummary,
  PassengerActiveResponse,
  Ride,
  RideWithPassengers,
} from '../../types/api';

/** Any payload shaped like `{ rides }` — summary, active-only, or a history page slice. */
type DriverRidesPayload = Pick<DriverActiveResponse, 'rides'>;

/** Any payload shaped like `{ bookings }` — summary, active-only, or a history page slice. */
type PassengerBookingsPayload = Pick<PassengerActiveResponse, 'bookings'>;

/**
 * Maps a single RideWithPassengers from the driver-summary endpoint
 * to the DriverBookingItem shape used by the UI.
 */
function mapRideWithPassengersToDriverItem(raw: RideWithPassengers): DriverBookingItem {
  const ride: Ride = {
    ride_id: raw.ride_id,
    origin_name: raw.origin_name ?? '',
    destination_name: raw.destination_name ?? '',
    departure_time: raw.departure_time,
    estimated_arrival_time: raw.estimated_arrival_time ?? null,
    available_seats: raw.available_seats,
    price: raw.price,
    status: raw.status as Ride['status'],
    group_id: raw.group_id ?? null,
    created_at: raw.departure_time,
    // Fields not returned by summary — safe defaults
    driver_id: '',
    distance_km: undefined,
    duration_min: undefined,
    route_coords: [],
    user_booking_status: null,
  };

  const passengers: PassengerInRide[] = raw.passengers.map((p) => ({
    bookingId: p.booking_id,
    passengerName: p.passenger_name,
    numSeats: p.num_seats,
    status: p.status,
    pickupName: p.pickup_name ?? null,
    pickupTime: p.pickup_time ?? null,
    dropoffName: p.destination_name ?? null,
  }));

  return { ride, passengers };
}

/**
 * Maps the full DriverSummaryResponse to a sorted list of DriverBookingItem.
 * Filters out rides with no passengers (nothing to show in driver tab).
 */
export function mapDriverSummaryToItems(response: DriverRidesPayload): DriverBookingItem[] {
  return response.rides
    .filter((r) => r.passengers.length > 0)
    .map(mapRideWithPassengersToDriverItem)
    .sort(
      (a, b) =>
        new Date(a.ride.departure_time).getTime() -
        new Date(b.ride.departure_time).getTime()
    );
}

/**
 * Maps a single PassengerBookingSummary from the passenger-summary endpoint
 * to the PassengerBookingItem shape used by the UI.
 */
function mapPassengerSummaryRowToItem(raw: PassengerBookingSummary): PassengerBookingItem {
  const ride: Ride = {
    ride_id: raw.ride_id,
    origin_name: raw.origin_name ?? '',
    destination_name: raw.destination_name ?? '',
    departure_time: raw.departure_time,
    estimated_arrival_time: raw.estimated_arrival_time ?? null,
    available_seats: 0,
    price: 0,
    status: raw.ride_status as Ride['status'],
    group_id: raw.group_id ?? null,
    created_at: raw.departure_time,
    // Fields not returned by summary — safe defaults
    driver_id: '',
    distance_km: undefined,
    duration_min: undefined,
    route_coords: [],
    user_booking_status: null,
  };

  return {
    ride,
    bookingId: raw.booking_id,
    bookingStatus: raw.booking_status,
    driverName: raw.driver?.full_name ?? null,
  };
}

/**
 * Maps the full PassengerSummaryResponse to a sorted list of PassengerBookingItem.
 */
export function mapPassengerSummaryToItems(response: PassengerBookingsPayload): PassengerBookingItem[] {
  return response.bookings
    .map(mapPassengerSummaryRowToItem)
    .sort(
      (a, b) =>
        new Date(a.ride.departure_time).getTime() -
        new Date(b.ride.departure_time).getTime()
    );
}
