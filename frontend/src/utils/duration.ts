/**
 */
export function formatDurationMinutes(min: number): string {
  const m = Math.round(Number(min)) || 0;
  if (m < 60) {
    return m === 0 ? 'פחות מדקה' : `${m} דק'`;
  }
  const hours = Math.floor(m / 60);
  const mins = m % 60;
  const hourWord = hours === 1 ? 'שעה' : hours === 2 ? 'שעתיים' : `${hours} שעות`;
  if (mins === 0) {
    return hourWord;
  }
  const minPart = `${mins} דק'`;
  return `${hourWord} ו-${minPart}`;
}
