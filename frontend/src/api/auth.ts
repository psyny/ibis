import { request, setToken } from './config';
import type { BankInfoType, Me, UserInfo } from './types';

export function login(login: string, password: string) {
  return request<{ token: string; user: UserInfo }>('/api/auth/login', { method: 'POST', body: { login, password } });
}

export function getMe() {
  return request<Me>('/api/auth/me');
}

export interface ProfileUpdate {
  display_name?: string;
  email?: string;
  whatsapp?: string;
  bank_info_type?: BankInfoType;
  bank_info?: string;
  transfer_qr?: string;
}

export function updateProfile(data: ProfileUpdate) {
  return request<Me>('/api/me', { method: 'PUT', body: data });
}

/** Changes the password and signs out other devices; this device gets a new token. */
export async function changePassword(current_password: string, new_password: string) {
  const { token } = await request<{ token: string }>('/api/me/password', {
    method: 'POST',
    body: { current_password, new_password },
  });
  setToken(token);
}

/** Signs out every other device (e.g. a lost phone); this device gets a new token. */
export async function signOutEverywhere() {
  const { token } = await request<{ token: string }>('/api/me/sign-out-everywhere', { method: 'POST' });
  setToken(token);
}
