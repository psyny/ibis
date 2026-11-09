import { request } from './config';
import type { RecurringTask, RecurringTaskInput, Task, TaskInput, TaskLabel } from './types';

const base = (householdId: string) => `/api/households/${householdId}`;

export interface TaskFilters {
  includeCompleted?: boolean;
  assigneeId?: string | null;
  /** YYYY-MM: only tasks due that month */
  dueMonth?: string | null;
  categoryId?: string | null;
  locationId?: string | null;
}

export function listTasks(hid: string, filters: TaskFilters = {}) {
  const params = new URLSearchParams();
  if (filters.includeCompleted) params.set('include_completed', 'true');
  if (filters.assigneeId) params.set('assignee_id', filters.assigneeId);
  if (filters.dueMonth) params.set('due_month', filters.dueMonth);
  if (filters.categoryId) params.set('category_id', filters.categoryId);
  if (filters.locationId) params.set('location_id', filters.locationId);
  const query = params.toString();
  return request<Task[]>(`${base(hid)}/tasks${query ? `?${query}` : ''}`);
}

export const getTask = (hid: string, id: string) => request<Task>(`${base(hid)}/tasks/${id}`);
export const createTask = (hid: string, data: TaskInput) => request<Task>(`${base(hid)}/tasks`, { method: 'POST', body: data });
export const updateTask = (hid: string, id: string, data: TaskInput) =>
  request<Task>(`${base(hid)}/tasks/${id}`, { method: 'PUT', body: data });
export const deleteTask = (hid: string, id: string) => request<void>(`${base(hid)}/tasks/${id}`, { method: 'DELETE' });
export const completeTask = (hid: string, id: string, done: boolean) =>
  request<Task>(`${base(hid)}/tasks/${id}/${done ? 'complete' : 'uncomplete'}`, { method: 'POST' });

export const listRecurringTasks = (hid: string) => request<RecurringTask[]>(`${base(hid)}/recurring-tasks`);
export const createRecurringTask = (hid: string, data: RecurringTaskInput) =>
  request<RecurringTask>(`${base(hid)}/recurring-tasks`, { method: 'POST', body: data });
export const updateRecurringTask = (hid: string, id: string, data: RecurringTaskInput) =>
  request<RecurringTask>(`${base(hid)}/recurring-tasks/${id}`, { method: 'PUT', body: data });
export const deleteRecurringTask = (hid: string, id: string) =>
  request<void>(`${base(hid)}/recurring-tasks/${id}`, { method: 'DELETE' });

// Task categories and locations (both lists in one call)
export const listTaskLabels = (hid: string) => request<TaskLabel[]>(`${base(hid)}/task-labels`);
export const createTaskLabel = (hid: string, data: { kind: TaskLabel['kind']; name: string }) =>
  request<TaskLabel>(`${base(hid)}/task-labels`, { method: 'POST', body: data });
export const renameTaskLabel = (hid: string, id: string, name: string) =>
  request<TaskLabel>(`${base(hid)}/task-labels/${id}`, { method: 'PUT', body: { name } });
export const deleteTaskLabel = (hid: string, id: string) => request<void>(`${base(hid)}/task-labels/${id}`, { method: 'DELETE' });
