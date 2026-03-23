export interface User {
  user_id: string;
  email: string;
  full_name?: string;
  first_name?: string;
  phone_number?: string;
  is_verified?: boolean;
  avatar_key?: string | null;
  avatar_url?: string | null;
  avatar_url_small?: string | null;
  avatar_url_medium?: string | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Ride {
  ride_id: string;
  driver_id: string;
  group_id?: string | null;
  group_name?: string | null;
  origin_name: string | null;
  destination_name: string | null;
  departure_time: string;
  estimated_arrival_time: string | null;
  available_seats: number;
  price: number;
  status: string;
  created_at: string;
  user_booking_status?: string | null;
  distance_km?: number;
  duration_min?: number;
  route_coords?: number[][];
  /** סיכום המסלול (כביש) – כמו ביצירת הנסיעה */
  route_summary?: string | null;
}

export interface RideSearchResponse {
  items: Ride[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface MessageResponse {
  message_id: number;
  conversation_id: string;
  sender_id: string;
  body: string;
  created_at: string;
}

export interface PaginatedMessagesResponse {
  items: MessageResponse[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface ConversationDetail {
  conversation_id: string;
  partner: {
    user_id: string;
    full_name: string;
    avatar_url?: string;
  };
  created_at: string;
  booking_id?: string;
  /** אם הבקאנד מחזיר – מוצג בכותרת הצ'אט (למשל מוצא ← יעד) */
  route_label?: string | null;
}

export interface ConversationListItem {
  conversation_id: string;
  partner: { user_id: string; full_name: string; avatar_url?: string };
  last_message_at: string | null;
  last_message_preview: string | null;
  has_unread?: boolean;
}

export interface PaginatedBookingsResponse {
  items: Booking[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface PassengerRequest {
  request_id: string;
  passenger_id: string;
  group_id?: string | null;
  num_passengers: number;
  pickup_name: string | null;
  destination_name: string | null;
  requested_departure_time: string;
  status: string;
  created_at: string;
  is_notification_active: boolean;
}

export interface RidePreviewResponse {
  session_id: string;
  origin_name: string;
  destination_name: string;
  origin_coords: number[];
  destination_coords: number[];
  routes: Array<{
    route_index: number;
    summary: string;
    duration_min: number;
    distance_km: number;
    coords: number[][];
  }>;
}

export interface AddressFromCoordsResponse {
  address: string;
  lat: number;
  lon: number;
}

export interface DriverInfo {
  full_name: string;
  phone_number: string | null;
}

export interface Booking {
  booking_id: string;
  ride_id: string;
  request_id: string;
  passenger_id: string;
  num_seats: number;
  status: string;
  reminder_sent: boolean;
  created_at: string;
  passenger_name?: string | null;
  phone?: string | null;
}

/** סוגי התראות לתצוגה ולמיפוי מהבקאנד. */
export type NotificationType =
  | 'booking_approved'
  | 'booking_rejected'
  | 'ride_cancelled'
  | 'booking_request'
  | 'booking_cancelled_by_passenger'
  | 'group_joined'
  | 'group_member_joined'
  | 'pending_approval';

export interface NotificationItem {
  type: string;
  title: string;
  body: string | null;
  created_at: string;
  booking_id: string;
  ride_id: string;
  other_party_name: string | null;
  ride_origin: string | null;
  ride_destination: string | null;
  status: string | null;
  /** אופציונלי — כשהבקאנד יחזיר; לסמן כנקרא. */
  id?: string;
  is_read?: boolean;
  action_url?: string;
}

export interface Group {
  group_id: string;
  name: string;
  invite_code: string;
  admin_id: string;
  is_active: boolean;
  max_members?: number | null;
  invite_expires_at?: string | null;
  created_at: string;
  member_count?: number;
  avatar_key?: string | null;
  avatar_url?: string | null;
  description?: string | null;
}

export interface GroupMember {
  id: string;
  group_id: string;
  user_id: string;
  role: 'admin' | 'member';
  joined_at: string;
  full_name?: string;
  avatar_url?: string | null;
}
