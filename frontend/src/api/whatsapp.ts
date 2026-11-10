import { request } from './config';
import type { AvailableWhatsAppGroup, OutgoingMessage, WhatsAppGroup, WhatsAppStatus } from './types';

const base = (hid: string) => `/api/households/${hid}/whatsapp`;

export const getWhatsAppStatus = (hid: string) => request<WhatsAppStatus>(base(hid));
export const connectWhatsApp = (hid: string) => request<WhatsAppStatus>(`${base(hid)}/connect`, { method: 'POST' });
export const disconnectWhatsApp = (hid: string) => request<WhatsAppStatus>(`${base(hid)}/disconnect`, { method: 'POST' });

export const listAvailableGroups = (hid: string) => request<AvailableWhatsAppGroup[]>(`${base(hid)}/available-groups`);
export const listWhatsAppGroups = (hid: string) => request<WhatsAppGroup[]>(`${base(hid)}/groups`);
export const addWhatsAppGroup = (hid: string, data: { jid: string; name: string }) =>
  request<WhatsAppGroup>(`${base(hid)}/groups`, { method: 'POST', body: data });
export const setWhatsAppGroupActive = (hid: string, id: string, is_active: boolean) =>
  request<WhatsAppGroup>(`${base(hid)}/groups/${id}`, { method: 'PUT', body: { is_active } });
export const removeWhatsAppGroup = (hid: string, id: string) =>
  request<void>(`${base(hid)}/groups/${id}`, { method: 'DELETE' });

/** Sends a test message right away to one household group or one member */
export const sendWhatsAppTest = (hid: string, target: { group_id: string } | { member_id: string }) =>
  request<void>(`${base(hid)}/test`, { method: 'POST', body: target });

export const listOutgoingMessages = (hid: string) => request<OutgoingMessage[]>(`${base(hid)}/messages`);
