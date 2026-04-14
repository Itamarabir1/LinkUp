import { z } from 'zod';

// --- Ride Status Events (channel: ride_{id}) ---
export const RideEventSchema = z
  .object({
    event: z.string(),
    ride_id: z.string(),
    status: z.string().optional(),
    color: z.string().optional(),
    message: z.string().optional(),
  })
  .passthrough();
export type RideEvent = z.infer<typeof RideEventSchema>;

// --- Driver Location Events (channel: booking_{id}) ---
export const DriverLocationEventSchema = z.object({
  type: z.literal('location_update'),
  ride_id: z.string().optional(),
  lat: z.number(),
  lng: z.number(),
  heading: z.number().optional(),
  speed: z.number().optional(),
  timestamp: z.string().optional(),
});
export type DriverLocationEvent = z.infer<typeof DriverLocationEventSchema>;

// --- Passenger Location Events (channel: ride_{id}:passenger_locations) ---
export const PassengerLocationEventSchema = z.object({
  type: z.literal('passenger_location'),
  booking_id: z.string(),
  passenger_id: z.string(),
  ride_id: z.string().optional(),
  lat: z.number(),
  lng: z.number(),
  heading: z.number().optional(),
  speed: z.number().optional(),
  timestamp: z.string().optional(),
});
export type PassengerLocationEvent = z.infer<typeof PassengerLocationEventSchema>;

// --- Chat / Presence Events (chat WebSocket) ---
export const UserOnlineEventSchema = z.object({
  type: z.literal('user_online'),
  user_id: z.string(),
});

export const UserOfflineEventSchema = z.object({
  type: z.literal('user_offline'),
  user_id: z.string(),
});

export const TypingStartEventSchema = z.object({
  type: z.literal('typing_start'),
  user_id: z.string(),
  conversation_id: z.string(),
  recipient_id: z.string(),
  full_name: z.string().optional(),
});

export const TypingStopEventSchema = z.object({
  type: z.literal('typing_stop'),
  user_id: z.string(),
  conversation_id: z.string(),
  recipient_id: z.string(),
});

export const UnreadCountEventSchema = z.object({
  type: z.literal('unread_count'),
});

export const ChatPresenceEventSchema = z.discriminatedUnion('type', [
  UserOnlineEventSchema,
  UserOfflineEventSchema,
  TypingStartEventSchema,
  TypingStopEventSchema,
  UnreadCountEventSchema,
]);
export type ChatPresenceEvent = z.infer<typeof ChatPresenceEventSchema>;

/** Chat message frame arriving over WS (parallel to API MessageResponse). */
export const ChatMessageSchema = z
  .object({
    message_id: z.number(),
    conversation_id: z.string(),
    sender_id: z.string(),
    body: z.string(),
    created_at: z.string(),
  })
  .passthrough();
export type ChatMessage = z.infer<typeof ChatMessageSchema>;

// --- Notifications WebSocket (FastAPI /notifications/ws) ---
export const NotificationRefreshEventSchema = z
  .object({
    type: z.literal('notifications_refresh'),
  })
  .strict();

// --- User Events (channel: user:{user_id}:events via chat-ws) ---
export const UserEventSchema = z
  .object({
    event: z.string(),
    user_id: z.string(),
    ride_id: z.string().optional(),
    booking_id: z.string().optional(),
    request_id: z.string().optional(),
    status: z.string().optional(),
  })
  .passthrough();
export type UserEvent = z.infer<typeof UserEventSchema>;
