import { describe, expect, it } from 'vitest';
import { getRideSourceLabel } from './rideDisplay';

describe('getRideSourceLabel', () => {
  it('returns ציבורי when no group id', () => {
    expect(getRideSourceLabel(null, [])).toBe('ציבורי');
    expect(getRideSourceLabel(undefined, [])).toBe('ציבורי');
  });

  it('returns group name when found', () => {
    expect(
      getRideSourceLabel('g1', [{ group_id: 'g1', name: 'הקבוצה שלי' }])
    ).toBe('הקבוצה שלי');
  });

  it('returns ציבורי when id not in list', () => {
    expect(getRideSourceLabel('unknown', [{ group_id: 'g2', name: 'אחר' }])).toBe('ציבורי');
  });
});
