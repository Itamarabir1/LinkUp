export function formatChatLastSeen(isoString: string | null | undefined): string {
  if (isoString == null || String(isoString).trim() === '') return '';
  const date = new Date(isoString);
  const t = date.getTime();
  if (Number.isNaN(t)) return '';
  const now = new Date();
  const diffMs = now.getTime() - t;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'לפני כמה שניות';
  if (diffMins < 60) return `לפני ${diffMins} דקות`;
  if (diffMins < 1440) return `לפני ${Math.floor(diffMins / 60)} שעות`;
  return `לפני ${Math.floor(diffMins / 1440)} ימים`;
}
