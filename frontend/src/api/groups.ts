import { api } from './client';
import type { Group, GroupMember } from '../types/api';
import type { Ride } from '../types/api';

// יצירת קבוצה חדשה (תיאור ותמונה אופציונליים; תמונה מעלה אחרי יצירה)
export async function createGroup(payload: {
  name: string;
  description?: string;
}): Promise<Group> {
  const { data } = await api.post<Group>('/groups', payload);
  return data;
}

// שליפת הקבוצות שלי
export async function getMyGroups(): Promise<Group[]> {
  const { data } = await api.get<Group[]>('/groups/my');
  return data;
}

// שליפת קבוצה לפי invite_code (לדף הצטרפות)
export async function getGroupByInviteCode(inviteCode: string): Promise<Group> {
  const { data } = await api.get<Group>(`/groups/join/${inviteCode}`);
  return data;
}

// הצטרפות לקבוצה
export async function joinGroup(inviteCode: string): Promise<Group> {
  const { data } = await api.post<Group>(`/groups/join/${inviteCode}`);
  return data;
}

// שליפת חברי קבוצה
export async function getGroupMembers(groupId: string): Promise<GroupMember[]> {
  const { data } = await api.get<GroupMember[]>(`/groups/${groupId}/members`);
  return data;
}

// הסרת חבר (מנהל בלבד)
export async function removeMember(groupId: string, userId: string): Promise<void> {
  await api.delete(`/groups/${groupId}/members/${userId}`);
}

// העלאת חבר למנהל
export async function promoteMember(groupId: string, userId: string): Promise<void> {
  await api.patch(`/groups/${groupId}/members/${userId}/promote`);
}

// עזיבת קבוצה
export async function leaveGroup(groupId: string): Promise<void> {
  await api.delete(`/groups/${groupId}/leave`);
}

// סגירת קבוצה (מנהל בלבד)
export async function closeGroup(groupId: string): Promise<void> {
  await api.delete(`/groups/${groupId}`);
}

// שינוי שם קבוצה (מנהל בלבד)
export async function renameGroup(groupId: string, name: string): Promise<Group> {
  const { data } = await api.patch<Group>(`/groups/${groupId}`, { name });
  return data;
}

// עדכון קבוצה (שם ו/או תיאור)
export async function updateGroup(
  groupId: string,
  payload: { name?: string; description?: string }
): Promise<Group> {
  const { data } = await api.patch<Group>(`/groups/${groupId}`, payload);
  return data;
}

// תמונת קבוצה — קבלת URL להעלאה
export async function getGroupImageUploadUrl(
  groupId: string
): Promise<{ upload_url: string; key: string }> {
  const { data } = await api.post<{ upload_url: string; key: string }>(
    `/groups/${groupId}/upload-image`
  );
  return data;
}

// אישור העלאת תמונה (אחרי PUT ל-upload_url)
export async function confirmGroupImage(
  groupId: string,
  key: string
): Promise<Group> {
  const { data } = await api.post<Group>(`/groups/${groupId}/confirm-image`, {
    key,
  });
  return data;
}

// מחיקת תמונת קבוצה
export async function deleteGroupImage(groupId: string): Promise<Group> {
  const { data } = await api.delete<Group>(`/groups/${groupId}/image`);
  return data;
}

// נסיעות של קבוצה (לטאב נסיעות במסך קבוצה)
export async function getGroupRides(groupId: string): Promise<Ride[]> {
  const { data } = await api.get<Ride[]>(`/groups/${groupId}/rides`);
  return data;
}
