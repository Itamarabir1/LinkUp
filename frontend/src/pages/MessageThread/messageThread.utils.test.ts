import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { formatChatLastSeen } from './messageThread.utils';

describe('formatChatLastSeen', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns empty for null or blank', () => {
    expect(formatChatLastSeen(null)).toBe('');
    expect(formatChatLastSeen('   ')).toBe('');
  });

  it('returns empty for invalid iso', () => {
    expect(formatChatLastSeen('invalid')).toBe('');
  });

  it('shows seconds wording when under one minute', () => {
    vi.setSystemTime(new Date('2026-06-01T12:00:30Z'));
    expect(formatChatLastSeen('2026-06-01T12:00:00Z')).toBe('לפני כמה שניות');
  });

  it('shows minutes when under one hour', () => {
    vi.setSystemTime(new Date('2026-06-01T13:00:00Z'));
    expect(formatChatLastSeen('2026-06-01T12:10:00Z')).toBe('לפני 50 דקות');
  });

  it('shows hours when under one day', () => {
    vi.setSystemTime(new Date('2026-06-03T10:00:00Z'));
    expect(formatChatLastSeen('2026-06-02T12:00:00Z')).toBe('לפני 22 שעות');
  });
});
