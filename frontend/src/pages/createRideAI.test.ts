/**
 * Unit tests for pure AI helper functions in useCreateRide.
 * No React, no jsdom — pure logic only.
 *
 * Run: npx vitest run src/pages/createRideAI.test.ts
 * Or:  npm test -- createRideAI
 */
import { describe, it, expect } from 'vitest';
import {
  extractSeatsFromText,
  resolveCreateRideFollowUpReason,
} from './useCreateRide';
import type { AISearchResult } from '../api/passengers';

describe('extractSeatsFromText', () => {
  it('extracts Hebrew מקומות', () => {
    expect(extractSeatsFromText('נסיעה עם 3 מקומות')).toBe(3);
  });

  it('extracts Hebrew נוסעים', () => {
    expect(extractSeatsFromText('2 נוסעים בבקשה')).toBe(2);
  });

  it('extracts English seats', () => {
    expect(extractSeatsFromText('ride with 4 seats')).toBe(4);
  });

  it('extracts English seat (singular)', () => {
    expect(extractSeatsFromText('1 seat available')).toBe(1);
  });

  it('clamps to max 8', () => {
    expect(extractSeatsFromText('10 מקומות')).toBe(8);
  });

  it('clamps to min 1', () => {
    expect(extractSeatsFromText('0 מקומות')).toBe(1);
  });

  it('returns null when no match', () => {
    expect(extractSeatsFromText('נסיעה מתל אביב לחיפה')).toBeNull();
  });

  it('returns null for empty string', () => {
    expect(extractSeatsFromText('')).toBeNull();
  });
});

function makeAI(overrides: Partial<AISearchResult> = {}): AISearchResult {
  return {
    pickup_name: 'תל אביב',
    destination_name: 'חיפה',
    departure_time: new Date(Date.now() + 86400000).toISOString(),
    departure_time_to: null,
    departure_date: null,
    destination_radius: null,
    search_radius: 3,
    confidence: 0.9,
    raw_interpretation: 'נסיעה מתל אביב לחיפה',
    needs_clarification: false,
    missing_fields: [],
    ambiguity_reasons: [],
    follow_up_question: null,
    ...overrides,
  };
}

describe('resolveCreateRideFollowUpReason', () => {
  it('returns null when all fields valid', () => {
    expect(resolveCreateRideFollowUpReason(makeAI())).toBeNull();
  });

  it('returns missing_location when pickup missing', () => {
    const ai = makeAI({ pickup_name: null });
    expect(resolveCreateRideFollowUpReason(ai)).toBe('missing_location');
  });

  it('returns missing_location when destination missing', () => {
    const ai = makeAI({ destination_name: null });
    expect(resolveCreateRideFollowUpReason(ai)).toBe('missing_location');
  });

  it('returns need_time when departure_date present but no time', () => {
    const ai = makeAI({
      departure_time: null,
      departure_date: '2026-04-18',
    });
    expect(resolveCreateRideFollowUpReason(ai)).toBe('need_time');
  });

  it('returns need_datetime when neither date nor time', () => {
    const ai = makeAI({
      departure_time: null,
      departure_date: null,
    });
    expect(resolveCreateRideFollowUpReason(ai)).toBe('need_datetime');
  });

  it('returns past_or_invalid when departure_time in past', () => {
    const ai = makeAI({
      departure_time: new Date(Date.now() - 3600000).toISOString(),
    });
    expect(resolveCreateRideFollowUpReason(ai)).toBe('past_or_invalid');
  });

  it('returns past_or_invalid when departure_time is invalid string', () => {
    const ai = makeAI({ departure_time: 'not-a-date' });
    expect(resolveCreateRideFollowUpReason(ai)).toBe('past_or_invalid');
  });
});
