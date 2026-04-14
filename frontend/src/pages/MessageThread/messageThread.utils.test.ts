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

  it('shows yesterday at time when previous local calendar day', () => {
    vi.setSystemTime(new Date(2026, 5, 3, 14, 0, 0));
    const past = new Date(2026, 5, 2, 10, 30, 0);
    const timeLabel = past.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
    expect(formatChatLastSeen(past.toISOString())).toBe(`אתמול בשעה ${timeLabel}`);
  });
});
