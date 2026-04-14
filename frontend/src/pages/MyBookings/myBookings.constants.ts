export const AVATAR_COLORS = [
  '#6366f1',
  '#059669',
  '#d97706',
  '#dc2626',
  '#7c3aed',
  '#0ea5e9',
] as const;

export const STATUS_LABEL: Record<string, string> = {
  pending_approval: 'ממתין לאישור',
  confirmed: 'אושר',
  rejected: 'נדחה',
  cancelled: 'בוטל',
  completed: 'הושלם',
};
