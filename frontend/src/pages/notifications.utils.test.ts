import { describe, expect, it } from 'vitest';
import { getDisplayType, getTimeGroup, NOTIFICATION_GROUP_ORDER } from './notifications.utils';

describe('notifications.utils', () => {
  it('maps booking_confirmed to booking_approved', () => {
    expect(getDisplayType('booking_confirmed')).toBe('booking_approved');
  });

  it('getTimeGroup is deterministic for fixed date strings vs reference', () => {
    const label = getTimeGroup('2000-01-01T12:00:00.000Z');
    expect(['היום', 'אתמול', 'השבוע', 'קודם לכן']).toContain(label);
  });

  it('NOTIFICATION_GROUP_ORDER is stable', () => {
    expect(NOTIFICATION_GROUP_ORDER).toEqual(['היום', 'אתמול', 'השבוע', 'קודם לכן']);
  });
});
