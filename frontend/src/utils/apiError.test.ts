import { describe, expect, it } from 'vitest';
import {
  getApiErrorMessage,
  isChatIdempotencyKeyMismatch,
  isTimeoutOrAbortError,
} from './apiError';

function axiosLike(detail: unknown, message?: unknown) {
  return { response: { data: message !== undefined ? { message, detail } : { detail } } };
}

describe('getApiErrorMessage', () => {
  it('returns Error.message when there is no response body', () => {
    expect(getApiErrorMessage(new Error('network down'), 'fallback')).toBe('network down');
  });

  it('returns fallback for unknown shapes without message', () => {
    expect(getApiErrorMessage({ foo: 1 }, 'fallback')).toBe('fallback');
  });

  it('prefers string message over detail when both exist', () => {
    const err = axiosLike('ignored', 'from message');
    expect(getApiErrorMessage(err, 'fallback')).toBe('from message');
  });

  it('uses string detail when present', () => {
    expect(getApiErrorMessage(axiosLike('bad request'), 'fallback')).toBe('bad request');
  });

  it('extracts first validation error msg from FastAPI-style array', () => {
    const err = axiosLike([{ type: 'value_error', msg: 'field required', loc: ['body', 'x'] }]);
    expect(getApiErrorMessage(err, 'fallback')).toBe('field required');
  });

  it('stringifies non-string array detail', () => {
    const err = axiosLike([1, 2]);
    expect(getApiErrorMessage(err, 'fallback')).toBe(JSON.stringify([1, 2]));
  });

  it('stringifies object detail', () => {
    const err = axiosLike({ code: 'X' });
    expect(getApiErrorMessage(err, 'fallback')).toBe(JSON.stringify({ code: 'X' }));
  });
});

describe('isChatIdempotencyKeyMismatch', () => {
  it('returns true when 422 detail.code is idempotency_key_mismatch', () => {
    expect(
      isChatIdempotencyKeyMismatch({
        response: {
          status: 422,
          data: {
            detail: { code: 'idempotency_key_mismatch', message: 'reuse' },
          },
        },
      })
    ).toBe(true);
  });

  it('returns false otherwise', () => {
    expect(
      isChatIdempotencyKeyMismatch({
        response: { status: 422, data: { detail: { code: 'other' } } },
      })
    ).toBe(false);
    expect(
      isChatIdempotencyKeyMismatch({
        response: { status: 409 },
      })
    ).toBe(false);
  });
});

describe('isTimeoutOrAbortError', () => {
  it('detects ECONNABORTED', () => {
    expect(isTimeoutOrAbortError({ code: 'ECONNABORTED' })).toBe(true);
  });
  it('detects timeout in message', () => {
    expect(isTimeoutOrAbortError(new Error('timeout of 5000ms exceeded'))).toBe(true);
  });
  it('returns false for normal errors', () => {
    expect(isTimeoutOrAbortError(new Error('bad'))).toBe(false);
    expect(isTimeoutOrAbortError({ response: { status: 400 } })).toBe(false);
  });
});
