export function formatChatLastSeen(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'לפני כמה שניות';
  if (diffMins < 60) return `לפני ${diffMins} דקות`;
  if (diffMins < 1440) return `לפני ${Math.floor(diffMins / 60)} שעות`;
  return `לפני ${Math.floor(diffMins / 1440)} ימים`;
}
