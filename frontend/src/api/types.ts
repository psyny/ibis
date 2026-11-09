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
  language: string;
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
  language: string;
  today: string;
  my_role: Role;
  my_member_id: string | null;
  /** can_add_task: add tasks and manage recurring tasks (managers and residents) */
  permissions: { can_add_cost: boolean; can_manage: boolean; can_add_task: boolean };
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
  language: string;
  member_count: number;
}

/** Only notes for now (read / unread). To-dos are household tasks. */
export type NotificationType = 'note';
export type NotificationBox = 'inbox' | 'deleted';

/** One item of the user's notification inbox. Known `kind`s are rendered from `data` in the UI language. */
export interface AppNotification {
  id: string;
  household_id: string | null;
  type: NotificationType;
  kind: string;
  /** English fallback text, for kinds the UI doesn't know */
  title: string;
  body: string | null;
  data: Record<string, unknown>;
  /** The household task this note is about (clicking opens it) */
  task_id: string | null;
  viewed_at: string | null;
  deleted_at: string | null;
  created_at: string;
}

export interface NotificationBarData {
  items: AppNotification[];
  unviewed_count: number;
}

/** completed = green, overdue = red (past due), expiring = yellow (due within warn_days) */
export type TaskStatus = 'completed' | 'overdue' | 'expiring' | 'pending';

/** An entry of the household's task categories or locations (managers edit the lists). */
export interface TaskLabel {
  id: string;
  kind: 'category' | 'location';
  name: string;
}

export interface TaskSettings {
  title: string;
  category_id: string | null;
  location_id: string | null;
  description: string | null;
  /** The task turns yellow (and can notify) this many days before it is due */
  warn_days: number;
  notify_expiring: boolean;
  notify_expired: boolean;
  assignee_ids: string[];
}

export interface Task extends TaskSettings {
  id: string;
  category_name: string | null;
  location_name: string | null;
  /** manual, recurring or month_payment (data then holds the payment) */
  kind: string;
  data: Record<string, unknown>;
  due_date: string | null;
  status: TaskStatus;
  recurring_task_id: string | null;
  created_by_user_id: string | null;
  created_by_name: string | null;
  created_at: string;
  completed_at: string | null;
  completed_by_name: string | null;
  can_edit: boolean;
  can_delete: boolean;
  can_complete: boolean;
}

export interface TaskInput extends TaskSettings {
  due_date: string | null;
}

export type FrequencyUnit = 'day' | 'week' | 'month';
/** everyone: managers and residents when each task is created; everyone_guests: plus guests */
export type AssignMode = 'selected' | 'everyone' | 'everyone_guests';

export interface RecurringTaskInput extends TaskSettings {
  start_date: string;
  interval: number;
  unit: FrequencyUnit;
  /** Each task is due this many days after its scheduled date (0 = on it) */
  due_offset_days: number;
  wait_for_previous: boolean;
  assign_mode: AssignMode;
  is_active: boolean;
}

export interface RecurringTask extends RecurringTaskInput {
  id: string;
  last_occurrence_date: string | null;
  next_date: string | null;
}
