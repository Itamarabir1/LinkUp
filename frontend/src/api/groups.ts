import { api } from './client';
import type { Group, GroupMember, PaginatedRidesResponse } from '../types/api';

// Create group (optional description; image upload after create)
export async function createGroup(payload: {
  name: string;
  description?: string;
}): Promise<Group> {
  const { data } = await api.post<Group>('/groups', payload);
  return data;
}

export async function getMyGroups(opts?: { signal?: AbortSignal }): Promise<Group[]> {
  const { data } = await api.get<Group[]>('/groups/my', { signal: opts?.signal });
  return data;
}

export async function getGroupByInviteCode(inviteCode: string, opts?: { signal?: AbortSignal }): Promise<Group> {
  const { data } = await api.get<Group>(`/groups/join/${inviteCode}`, { signal: opts?.signal });
  return data;
}

// Join group
export async function joinGroup(inviteCode: string): Promise<Group> {
  const { data } = await api.post<Group>(`/groups/join/${inviteCode}`);
  return data;
}

export async function getGroupMembers(groupId: string, opts?: { signal?: AbortSignal }): Promise<GroupMember[]> {
  const { data } = await api.get<GroupMember[]>(`/groups/${groupId}/members`, { signal: opts?.signal });
  return data;
}

// Remove member (admin only)
export async function removeMember(groupId: string, userId: string): Promise<void> {
  await api.delete(`/groups/${groupId}/members/${userId}`);
}

// Promote member to admin
export async function promoteMember(groupId: string, userId: string): Promise<void> {
  await api.patch(`/groups/${groupId}/members/${userId}/promote`);
}

// Leave group
export async function leaveGroup(groupId: string): Promise<void> {
  await api.delete(`/groups/${groupId}/leave`);
}

// Close group (admin only)
export async function closeGroup(groupId: string): Promise<void> {
  await api.delete(`/groups/${groupId}`);
}

// Rename group (admin only)
export async function renameGroup(groupId: string, name: string): Promise<Group> {
  const { data } = await api.patch<Group>(`/groups/${groupId}`, { name });
  return data;
}

// Update group (name and/or description)
export async function updateGroup(
  groupId: string,
  payload: { name?: string; description?: string }
): Promise<Group> {
  const { data } = await api.patch<Group>(`/groups/${groupId}`, payload);
  return data;
}

// Group image — presigned upload URL
export async function getGroupImageUploadUrl(
  groupId: string
): Promise<{ upload_url: string; key: string }> {
  const { data } = await api.post<{ upload_url: string; key: string }>(
    `/groups/${groupId}/upload-image`
  );
  return data;
}

// Confirm image after PUT to upload_url
export async function confirmGroupImage(
  groupId: string,
  key: string
): Promise<Group> {
  const { data } = await api.post<Group>(`/groups/${groupId}/confirm-image`, {
    key,
  });
  return data;
}

// Delete group image
export async function deleteGroupImage(groupId: string): Promise<Group> {
  const { data } = await api.delete<Group>(`/groups/${groupId}/image`);
  return data;
}

export async function getGroupRides(
  groupId: string,
  params?: { limit?: number; after?: string; signal?: AbortSignal }
): Promise<PaginatedRidesResponse> {
  const { signal, ...rest } = params ?? {};
  const { data } = await api.get<PaginatedRidesResponse>(`/groups/${groupId}/rides`, {
    params: {
      limit: rest.limit ?? 20,
      after: rest.after,
    },
    signal,
  });
  return data;
}
