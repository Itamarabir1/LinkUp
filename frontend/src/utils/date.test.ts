import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import {
  formatConversationTime,
  formatDateTimeNoSeconds,
  formatRelativeNotificationTime,
  formatRideDate,
} from './date';

describe('formatDateTimeNoSeconds', () => {
  it('returns empty string for invalid input', () => {
    expect(formatDateTimeNoSeconds('not-a-date')).toBe('');
  });

  it('formats valid ISO string without seconds (locale calendar)', () => {
    const s = formatDateTimeNoSeconds('2026-02-16T09:05:44');
    expect(s).toMatch(/^\d{1,2}\.\d{1,2}\.2026, \d{2}:\d{2}$/);
  });
});

describe('formatRideDate', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns empty for invalid date', () => {
    expect(formatRideDate('')).toBe('');
  });

  it('shows היום for same local calendar day', () => {
    const now = new Date(2026, 5, 10, 14, 0, 0);
    vi.setSystemTime(now);
    const ride = new Date(2026, 5, 10, 8, 30, 0);
    expect(formatRideDate(ride)).toBe('היום 08:30');
  });

  it('shows מחר for next local day', () => {
    const now = new Date(2026, 5, 10, 14, 0, 0);
    vi.setSystemTime(now);
    const ride = new Date(2026, 5, 11, 7, 30, 0);
    expect(formatRideDate(ride)).toBe('מחר 07:30');
  });
});

describe('formatConversationTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns empty for null', () => {
    expect(formatConversationTime(null)).toBe('');
  });

  it('uses minutes ago when under one hour', () => {
    const now = new Date(2026, 3, 1, 12, 0, 0);
    vi.setSystemTime(now);
    const past = new Date(2026, 3, 1, 11, 15, 0);
    expect(formatConversationTime(past)).toBe('לפני 45 דקות');
  });

  it('shows HH:mm for same calendar day', () => {
    const now = new Date(2026, 3, 1, 18, 0, 0);
    vi.setSystemTime(now);
    const past = new Date(2026, 3, 1, 9, 5, 0);
    expect(formatConversationTime(past)).toBe('09:05');
  });
});

describe('formatRelativeNotificationTime', () => {
  it('returns empty string for invalid date', () => {
    expect(formatRelativeNotificationTime('')).toBe('');
    expect(formatRelativeNotificationTime('not-a-date')).toBe('');
  });

  it('returns "עכשיו" for current time', () => {
    expect(formatRelativeNotificationTime(new Date().toISOString())).toBe('עכשיו');
  });
});
