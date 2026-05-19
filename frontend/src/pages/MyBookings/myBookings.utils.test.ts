import { describe, expect, it } from 'vitest';
import {
  avatarInitial,
  canDriverShare,
  canPassengerShare,
  formatPickupDropoffLine,
} from './myBookings.utils';

describe('canPassengerShare', () => {
  it('is true only when booking confirmed and ride active', () => {
    expect(canPassengerShare('confirmed', 'active')).toBe(true);
    expect(canPassengerShare('pending', 'active')).toBe(false);
    expect(canPassengerShare('confirmed', 'completed')).toBe(false);
  });
});

describe('canDriverShare', () => {
  it('is true when at least one confirmed passenger', () => {
    expect(canDriverShare(0)).toBe(false);
    expect(canDriverShare(1)).toBe(true);
    expect(canDriverShare(3)).toBe(true);
  });
});

describe('formatPickupDropoffLine', () => {
  const t = (key: 'bookings:pickup' | 'bookings:dropoff') =>
    key === 'bookings:pickup' ? 'עולה' : 'יורד';

  it('joins pickup and dropoff with separator', () => {
    expect(formatPickupDropoffLine('תל אביב', 'חיפה', t)).toBe('עולה: תל אביב · יורד: חיפה');
  });

  it('returns only pickup when dropoff missing', () => {
    expect(formatPickupDropoffLine('תל אביב', null, t)).toBe('עולה: תל אביב');
  });

  it('returns empty string when both missing', () => {
    expect(formatPickupDropoffLine(undefined, undefined, t)).toBe('');
  });
});

describe('avatarInitial', () => {
  it('returns first character uppercased', () => {
    expect(avatarInitial('דני')).toBe('ד');
    expect(avatarInitial('abc')).toBe('A');
  });

  it('uses נ when name empty', () => {
    expect(avatarInitial('')).toBe('נ');
  });
});
