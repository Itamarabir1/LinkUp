/**
 * Tests for AI search state management in useSearchRides.
 * Tests cover: parseWithAI flow, resetAI, conversation history,
 * form prefill behavior.
 * Uses vi.mock for API calls.
 *
 * @vitest-environment jsdom
 */
import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import type { AISearchResult } from '../../api/passengers';

// Mock the passengers API
vi.mock('../../api/passengers', () => ({
  searchRides: vi.fn(),
  saveSearchAlert: vi.fn(),
  requestRideFromSearch: vi.fn(),
  parseRideSearchWithAI: vi.fn(),
}));

// Mock geo API
vi.mock('../../api/geo', () => ({
  fetchAddressFromCoords: vi.fn(),
}));

vi.mock('../../api/rides', () => ({
  fetchPassengerDriverInfo: vi.fn(),
}));

vi.mock('react-i18next', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-i18next')>();
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
    }),
  };
});

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useParams: () => ({}),
}));

import { useSearchRides } from './useSearchRides';
import { parseRideSearchWithAI } from '../../api/passengers';

const mockParseAI = parseRideSearchWithAI as ReturnType<typeof vi.fn>;

const makeResult = (
  overrides: Partial<AISearchResult> = {}
): AISearchResult => ({
  pickup_name: 'תל אביב',
  destination_name: 'חיפה',
  departure_time: '2026-04-18T08:00:00+03:00',
  departure_time_to: null,
  departure_date: null,
  destination_radius: null,
  search_radius: null,
  confidence: 0.95,
  raw_interpretation: 'הבנתי: נסיעה מתל אביב לחיפה',
  needs_clarification: false,
  missing_fields: [],
  ambiguity_reasons: [],
  follow_up_question: null,
  ...overrides,
});

describe('useSearchRides — AI search', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('prefills pickup and destination on successful parse', async () => {
    mockParseAI.mockResolvedValueOnce({ data: makeResult() });

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('טרמפ מתל אביב לחיפה מחר');
    });

    await act(async () => {
      await result.current.parseWithAI();
    });

    expect(result.current.pickup).toBe('תל אביב');
    expect(result.current.destination).toBe('חיפה');
  });

  it('sets aiResult after successful parse', async () => {
    const res = makeResult();
    mockParseAI.mockResolvedValueOnce({ data: res });

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('שאלה');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    expect(result.current.aiResult).toEqual(res);
  });

  it('clears textarea when follow_up_question received', async () => {
    mockParseAI.mockResolvedValueOnce({
      data: makeResult({
        pickup_name: null,
        needs_clarification: true,
        follow_up_question: 'מאיפה אתה יוצא?',
      }),
    });

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('לחיפה מחר');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    expect(result.current.aiQuery).toBe('');
  });

  it('does not clear textarea when parse succeeds (no follow_up)', async () => {
    mockParseAI.mockResolvedValueOnce({ data: makeResult() });

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('טרמפ מתל אביב לחיפה מחר');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    // textarea stays so user can see what they typed
    expect(result.current.aiQuery).toBe('טרמפ מתל אביב לחיפה מחר');
  });

  it('builds conversation history after exchange', async () => {
    mockParseAI.mockResolvedValueOnce({
      data: makeResult({
        pickup_name: null,
        follow_up_question: 'מאיפה אתה יוצא?',
        needs_clarification: true,
      }),
    });

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('לחיפה מחר');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    expect(result.current.conversationHistory.length).toBeGreaterThan(0);
    expect(
      result.current.conversationHistory.some(
        (t) => t.role === 'assistant'
      )
    ).toBe(true);
  });

  it('sends conversation_history in second turn', async () => {
    // First turn: missing pickup
    mockParseAI.mockResolvedValueOnce({
      data: makeResult({
        pickup_name: null,
        follow_up_question: 'מאיפה אתה יוצא?',
        needs_clarification: true,
      }),
    });

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('לחיפה מחר');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    // Second turn: user answers
    mockParseAI.mockResolvedValueOnce({ data: makeResult() });

    await act(async () => {
      result.current.setAiQuery('מתל אביב');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    const secondCall = mockParseAI.mock.calls[1][0];
    expect(secondCall.conversation_history.length).toBeGreaterThan(0);
  });

  it('sets aiError on API failure', async () => {
    mockParseAI.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('שאלה');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    expect(result.current.aiError).toBeTruthy();
    expect(result.current.aiResult).toBeNull();
  });

  it('resetAI clears all AI state', async () => {
    mockParseAI.mockResolvedValueOnce({ data: makeResult() });

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('שאלה');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    await act(async () => {
      result.current.resetAI();
    });

    expect(result.current.aiQuery).toBe('');
    expect(result.current.aiResult).toBeNull();
    expect(result.current.aiError).toBe('');
    expect(result.current.conversationHistory).toHaveLength(0);
  });

  it('does nothing when aiQuery is empty', async () => {
    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      await result.current.parseWithAI();
    });

    expect(mockParseAI).not.toHaveBeenCalled();
  });

  it('does not prefill date when departure_time is null', async () => {
    mockParseAI.mockResolvedValueOnce({
      data: makeResult({ departure_time: null }),
    });

    const { result } = renderHook(() => useSearchRides());
    const dateBefore = result.current.selectedDate;

    await act(async () => {
      result.current.setAiQuery('טרמפ מתל אביב לחיפה');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    // Date should not change if AI returned null
    expect(result.current.selectedDate).toEqual(dateBefore);
  });

  it('clamps search_radius to integer between 1-50', async () => {
    mockParseAI.mockResolvedValueOnce({
      data: makeResult({ search_radius: 47.8 }),
    });

    const { result } = renderHook(() => useSearchRides());

    await act(async () => {
      result.current.setAiQuery('לאזור חיפה');
    });
    await act(async () => {
      await result.current.parseWithAI();
    });

    expect(result.current.searchRadius).toBe(48);
    expect(result.current.searchRadius).toBeGreaterThanOrEqual(1);
    expect(result.current.searchRadius).toBeLessThanOrEqual(50);
  });
});
