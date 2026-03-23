import type { ChipItem } from '../../components/Chips/Chips';

export const GROUP_AVATAR_COLORS = [
  '#6366f1',
  '#059669',
  '#d97706',
  '#dc2626',
  '#7c3aed',
  '#0ea5e9',
] as const;

export const MEMBERS_PREVIEW = 8;

export const DATE_CHIP_ITEMS: ChipItem[] = [
  { id: 'all', label: 'הכל' },
  { id: 'today', label: 'היום' },
  { id: 'tomorrow', label: 'מחר' },
  { id: 'week', label: 'השבוע' },
];
