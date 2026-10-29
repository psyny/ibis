export type Role = 'manager' | 'resident' | 'guest' | 'viewer';

/** 'pix': bank_info is a PIX key (used to generate payment QR codes). 'other': free text. */
export type BankInfoType = 'pix' | 'other';

export interface UserInfo {
  id: string;
  login_name: string;
  display_name: string;
  is_active: boolean;
  is_admin: boolean;
  email: string | null;
  whatsapp: string | null;
  bank_info_type: BankInfoType;
  bank_info: string | null;
  created_at?: string | null;
  last_login_at?: string | null;
}

export interface MyHousehold {
  id: string;
  name: string;
  currency: string;
  role: Role;
  member_id: string | null;
}

export interface Me extends UserInfo {
  transfer_qr: string | null;
  households: MyHousehold[];
}

export interface Household {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  auto_close_days: number | null;
  shield_costs_from_guests: boolean;
  today: string;
  my_role: Role;
  my_member_id: string | null;
  permissions: { can_add_cost: boolean; can_manage: boolean };
  member_count: number;
}

export interface Member {
  id: string;
  user_id: string;
  login_name: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  is_participant: boolean;
  email: string | null;
  whatsapp: string | null;
  bank_info_type: BankInfoType;
  bank_info: string | null;
  has_transfer_qr: boolean;
}

export interface MemberDetail extends Member {
  transfer_qr: string | null;
}

export interface Category {
  id: string;
  name: string;
  color: string | null;
  is_archived: boolean;
}

export interface Preset {
  id: string;
  name: string;
  category_id: string | null;
  default_amount: number | null;
}

export interface Cost {
  id: string;
  description: string;
  category_id: string | null;
  category_name: string | null;
  amount: number;
  date: string;
  payer_ids: string[];
  coverer_ids: string[];
  paid_share: number;
  cover_share: number;
  source: string;
  recurring_cost_id: string | null;
  created_by_user_id: string | null;
  created_at: string | null;
  can_edit: boolean;
}

export interface CostInput {
  description: string;
  category_id: string | null;
  amount: number;
  date: string;
  payer_ids: string[];
  coverer_ids: string[];
}

export interface RecurringCost {
  id: string;
  description: string;
  category_id: string | null;
  category_name: string | null;
  amount: number;
  day_of_month: number;
  payer_ids: string[];
  coverer_ids: string[];
  is_active: boolean;
}

export interface RecurringCostInput {
  description: string;
  category_id: string | null;
  amount: number;
  day_of_month: number;
  payer_ids: string[];
  coverer_ids: string[];
  is_active: boolean;
}

export interface MonthInfo {
  id: string;
  year: number;
  month: number;
  status: 'open' | 'closed';
  closed_at: string | null;
  auto_close_on: string | null;
  cost_count: number;
  total: number;
}

export interface Balance {
  member_id: string;
  paid: number;
  covered: number;
  net: number;
}

export interface Transfer {
  from_member_id: string;
  to_member_id: string;
  amount: number;
}

export interface CategoryTotal {
  category_id: string | null;
  name: string;
  color: string | null;
  total: number;
}

export interface MonthSummary {
  month: MonthInfo;
  currency: string;
  total: number;
  members: Member[];
  balances: Balance[];
  transfers: Transfer[];
  category_totals: CategoryTotal[];
  categories: Category[];
  costs: Cost[];
  can_add_cost: boolean;
  can_manage: boolean;
  /** Guest in a household that shields costs: only what involves them, no category totals */
  restricted: boolean;
}

export interface AdminHousehold {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  auto_close_days: number | null;
  member_count: number;
}
