/** קבוצות למיפוי שם תצוגה (מקור נסיעה / בקשה) */
export type GroupNameRef = { group_id: string; name: string };

/**
 * תווית מקור לנסיעה או בקשה: שם קבוצה או "ציבורי".
 */
export function getRideSourceLabel(
  groupId: string | null | undefined,
  myGroups: GroupNameRef[]
): string {
  if (!groupId) return 'ציבורי';
  const g = myGroups.find((x) => x.group_id === groupId);
  return g?.name ?? 'ציבורי';
}
