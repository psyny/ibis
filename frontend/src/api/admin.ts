import { request } from './config';
import type { AdminHousehold, UserInfo } from './types';

export const listAllHouseholds = () => request<AdminHousehold[]>('/api/admin/households');
export const createHousehold = (data: { name: string; currency: string; timezone: string; auto_close_days: number | null }) =>
  request<AdminHousehold>('/api/admin/households', { method: 'POST', body: data });
export const deleteHousehold = (id: string) => request<void>(`/api/admin/households/${id}`, { method: 'DELETE' });

export const listUsers = () => request<UserInfo[]>('/api/admin/users');
export const createUser = (data: { login_name: string; display_name: string; password: string; is_admin: boolean }) =>
  request<UserInfo>('/api/admin/users', { method: 'POST', body: data });
export const updateUser = (
  id: string,
  data: { display_name?: string; is_active?: boolean; is_admin?: boolean; new_password?: string },
) => request<UserInfo>(`/api/admin/users/${id}`, { method: 'PUT', body: data });
