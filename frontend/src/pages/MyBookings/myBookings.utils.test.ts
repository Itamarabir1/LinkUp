import { describe, expect, it } from 'vitest';
import { avatarInitial, canDriverShare, canPassengerShare } from './myBookings.utils';

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

describe('avatarInitial', () => {
  it('returns first character uppercased', () => {
    expect(avatarInitial('דני')).toBe('ד');
    expect(avatarInitial('abc')).toBe('A');
  });

  it('uses נ when name empty', () => {
    expect(avatarInitial('')).toBe('נ');
  });
});
