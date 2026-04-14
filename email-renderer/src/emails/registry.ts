import BookingApproved from './templates/BookingApproved';
import BookingRejected from './templates/BookingRejected';
import ConversationSummary from './templates/ConversationSummary';
import NewRideRequest from './templates/NewRideRequest';
import PassengerCancelled from './templates/PassengerCancelled';
import PasswordReset from './templates/PasswordReset';
import RideCancelledByDriver from './templates/RideCancelledByDriver';
import RideCreatedForPassengers from './templates/RideCreatedForPassengers';
import RideReminderDriver from './templates/RideReminderDriver';
import RideReminderPassenger from './templates/RideReminderPassenger';
import VerifyEmail from './templates/VerifyEmail';
import Welcome from './templates/Welcome';
import type { ComponentType } from 'react';
import { EMAIL_MAP_KEYS } from './emailMapKeys';

export const TEMPLATE_REGISTRY: Record<string, ComponentType<any>> = {
  VerifyEmail,
  Welcome,
  PasswordReset,
  BookingApproved,
  BookingRejected,
  NewRideRequest,
  PassengerCancelled,
  RideCancelledByDriver,
  RideCreatedForPassengers,
  RideReminderDriver,
  RideReminderPassenger,
  ConversationSummary,
};

const missing = EMAIL_MAP_KEYS.filter((k) => !(k in TEMPLATE_REGISTRY));
if (missing.length > 0) {
  throw new Error(`[email-renderer] Missing templates in registry: ${missing.join(', ')}`);
}
