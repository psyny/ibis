import { request } from './config';
import type {
  BankInfoType,
  Category,
  Cost,
  CostInput,
  Household,
  Member,
  MemberDetail,
  MonthInfo,
  MonthSummary,
  Preset,
  RecurringCost,
  RecurringCostInput,
  Role,
} from './types';

const base = (householdId: string) => `/api/households/${householdId}`;

// Household
export const getHousehold = (hid: string) => request<Household>(base(hid));
export const updateHousehold = (
  hid: string,
  data: { name?: string; currency?: string; timezone?: string; auto_close_days?: number | null; disable_auto_close?: boolean },
) => request<Household>(base(hid), { method: 'PUT', body: data });

// Members
export const listMembers = (hid: string) => request<Member[]>(`${base(hid)}/members`);
export const getMember = (hid: string, mid: string) => request<MemberDetail>(`${base(hid)}/members/${mid}`);
export const createMember = (
  hid: string,
  data: { login_name: string; display_name?: string; password?: string; role: Role; email?: string; whatsapp?: string },
) => request<Member>(`${base(hid)}/members`, { method: 'POST', body: data });
export interface MemberUpdate {
  role?: Role;
  is_active?: boolean;
  display_name?: string;
  email?: string;
  whatsapp?: string;
  bank_info_type?: BankInfoType;
  bank_info?: string;
}
export const updateMember = (hid: string, mid: string, data: MemberUpdate) =>
  request<Member>(`${base(hid)}/members/${mid}`, { method: 'PUT', body: data });
export const resetMemberPassword = (hid: string, mid: string, new_password: string) =>
  request<void>(`${base(hid)}/members/${mid}/password`, { method: 'POST', body: { new_password } });

// Categories
export const listCategories = (hid: string, includeArchived = false) =>
  request<Category[]>(`${base(hid)}/categories?include_archived=${includeArchived}`);
export const createCategory = (hid: string, data: { name: string; color?: string }) =>
  request<Category>(`${base(hid)}/categories`, { method: 'POST', body: data });
export const updateCategory = (hid: string, id: string, data: { name?: string; color?: string; is_archived?: boolean }) =>
  request<Category>(`${base(hid)}/categories/${id}`, { method: 'PUT', body: data });
export const deleteCategory = (hid: string, id: string) =>
  request<{ deleted: boolean; archived: boolean }>(`${base(hid)}/categories/${id}`, { method: 'DELETE' });

// Presets (premade descriptions)
export const listPresets = (hid: string) => request<Preset[]>(`${base(hid)}/presets`);
export const createPreset = (hid: string, data: { name: string; category_id?: string | null; default_amount?: number | null }) =>
  request<Preset>(`${base(hid)}/presets`, { method: 'POST', body: data });
export const updatePreset = (
  hid: string,
  id: string,
  data: {
    name?: string;
    category_id?: string | null;
    default_amount?: number | null;
    clear_category?: boolean;
    clear_default_amount?: boolean;
  },
) => request<Preset>(`${base(hid)}/presets/${id}`, { method: 'PUT', body: data });
export const deletePreset = (hid: string, id: string) => request<void>(`${base(hid)}/presets/${id}`, { method: 'DELETE' });

// Months
export const listMonths = (hid: string) => request<MonthInfo[]>(`${base(hid)}/months`);
export const createMonth = (hid: string, year: number, month: number) =>
  request<MonthInfo>(`${base(hid)}/months`, { method: 'POST', body: { year, month } });
export const getMonthSummary = (hid: string, year: number, month: number) =>
  request<MonthSummary>(`${base(hid)}/months/${year}/${month}/summary`);
export const closeMonth = (hid: string, year: number, month: number) =>
  request<MonthInfo>(`${base(hid)}/months/${year}/${month}/close`, { method: 'POST' });
export const reopenMonth = (hid: string, year: number, month: number) =>
  request<MonthInfo>(`${base(hid)}/months/${year}/${month}/reopen`, { method: 'POST' });
export const applyRecurring = (hid: string, year: number, month: number) =>
  request<{ added: number }>(`${base(hid)}/months/${year}/${month}/apply-recurring`, { method: 'POST' });

// Costs
export const getCost = (hid: string, id: string) => request<Cost>(`${base(hid)}/costs/${id}`);
export const createCost = (hid: string, data: CostInput) => request<Cost>(`${base(hid)}/costs`, { method: 'POST', body: data });
export const updateCost = (hid: string, id: string, data: CostInput) =>
  request<Cost>(`${base(hid)}/costs/${id}`, { method: 'PUT', body: data });
export const deleteCost = (hid: string, id: string) => request<void>(`${base(hid)}/costs/${id}`, { method: 'DELETE' });

// Starting state (recurring costs)
export const listRecurring = (hid: string) => request<RecurringCost[]>(`${base(hid)}/recurring-costs`);
export const createRecurring = (hid: string, data: RecurringCostInput) =>
  request<RecurringCost>(`${base(hid)}/recurring-costs`, { method: 'POST', body: data });
export const updateRecurring = (hid: string, id: string, data: RecurringCostInput) =>
  request<RecurringCost>(`${base(hid)}/recurring-costs/${id}`, { method: 'PUT', body: data });
export const deleteRecurring = (hid: string, id: string) =>
  request<void>(`${base(hid)}/recurring-costs/${id}`, { method: 'DELETE' });
