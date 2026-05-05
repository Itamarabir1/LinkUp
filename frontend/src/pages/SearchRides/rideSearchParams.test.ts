import { describe, it, expect } from 'vitest';
import {
  buildManualRideSearchParams,
  buildParamsFromAiResult,
  formatLocalCalendarYmd,
} from './useSearchRides';

describe('formatLocalCalendarYmd', () => {
  it('formats local calendar date', () => {
    const d = new Date(2026, 4, 2, 15, 30, 0); // May 2 local
    expect(formatLocalCalendarYmd(d)).toBe('2026-05-02');
  });
});

describe('buildParamsFromAiResult', () => {
  it('uses departure_date only when AI gives date without time', () => {
    const p = buildParamsFromAiResult(
      {
        pickup_name: 'תל אביב',
        destination_name: 'חיפה',
        departure_time: null,
        departure_time_to: null,
        departure_date: '2026-05-10',
        destination_radius: null,
        search_radius: 3,
        confidence: 1,
        raw_interpretation: '',
        needs_clarification: false,
        missing_fields: [],
        ambiguity_reasons: [],
        follow_up_question: null,
      },
      {}
    );
    expect(p).not.toBeNull();
    expect(p!.departure_date).toBe('2026-05-10');
    expect(p!.departure_time).toBeUndefined();
    expect(p!.departure_time_to).toBeUndefined();
  });

  it('sends explicit range when both endpoints exist', () => {
    const p = buildParamsFromAiResult(
      {
        pickup_name: 'A',
        destination_name: 'B',
        departure_time: '2026-05-10T08:00:00.000Z',
        departure_time_to: '2026-05-10T18:00:00.000Z',
        departure_date: null,
        destination_radius: null,
        search_radius: 2,
        confidence: 1,
        raw_interpretation: '',
        needs_clarification: false,
        missing_fields: [],
        ambiguity_reasons: [],
        follow_up_question: null,
      },
      {}
    );
    expect(p!.departure_time).toBe('2026-05-10T08:00:00.000Z');
    expect(p!.departure_time_to).toBe('2026-05-10T18:00:00.000Z');
  });
});

describe('buildManualRideSearchParams', () => {
  const base = {
    pickup: 'תל אביב',
    destination: 'חיפה',
    searchRadius: 2,
    selectedDate: new Date('2026-05-10T12:00:00.000Z'),
    departureDateOnly: new Date(2026, 4, 11, 9, 0, 0),
    selectedDateTo: new Date('2026-05-10T20:00:00.000Z'),
  };

  it('date_only maps to departure_date only', () => {
    const p = buildManualRideSearchParams({
      ...base,
      searchMode: 'date_only',
    });
    expect(p.departure_date).toBe('2026-05-11');
    expect(p.departure_time).toBeUndefined();
    expect(p.departure_time_to).toBeUndefined();
  });

  it('time_range sends departure_time and departure_time_to', () => {
    const p = buildManualRideSearchParams({
      ...base,
      searchMode: 'time_range',
    });
    expect(p.departure_time).toBe(base.selectedDate.toISOString());
    expect(p.departure_time_to).toBe(base.selectedDateTo!.toISOString());
    expect(p.departure_date).toBeUndefined();
  });

  it('datetime sends departure_time only', () => {
    const p = buildManualRideSearchParams({
      ...base,
      searchMode: 'datetime',
    });
    expect(p.departure_time).toBe(base.selectedDate.toISOString());
    expect(p.departure_date).toBeUndefined();
    expect(p.departure_time_to).toBeUndefined();
  });
});
