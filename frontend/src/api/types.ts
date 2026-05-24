export type Role =
  | "employee"
  | "manager"
  | "tenant_admin"
  | "labor_inspector"
  | "supervisor"
  | "admin";

export type UserScope = "tenant" | "platform";
export type ClockInType = "entrada" | "salida";
export type BreakType = "inicio_parada" | "fin_parada";
export type LeaveStatus = "pending" | "approved" | "rejected" | "cancelled";
export type ShiftPatternType =
  | "rigid"
  | "rotating"
  | "split"
  | "night"
  | "mixed";

export interface Employee {
  id: string;
  company_id?: string;
  department_id: string | null;
  phone: string;
  email: string | null;
  full_name: string;
  id_document: string | null;
  employee_code: string;
  role: Role;
  supervisor_id: string | null;
  vacation_days_balance: number;
  is_active: boolean;
  shift_configuration_id: string | null;
  work_start_time: string | null;
  work_end_time: string | null;
  work_days: number[];
  work_schedule_blocks: WorkScheduleBlock[];
  work_schedule_periods: WorkSchedulePeriod[];
  rotating_shift: boolean;
  weekly_hours: number | null;
  created_at: string;
  updated_at: string;
}

/** @deprecated Resumen legacy; usar work_schedule_periods */
export interface WorkScheduleBlock {
  work_days: number[];
  work_start_time: string;
  work_end_time: string;
  break_minutes: number;
}

export interface WorkScheduleTimeSlot {
  work_start_time: string;
  work_end_time: string;
  break_minutes: number;
}

export interface WorkScheduleDayBlock {
  work_days: number[];
  slots: WorkScheduleTimeSlot[];
}

export interface WorkSchedulePeriod {
  valid_from: string;
  valid_to: string | null;
  blocks: WorkScheduleDayBlock[];
}

export interface ClockIn {
  id: string;
  employee_id: string;
  record_type: ClockInType;
  recorded_at: string;
  latitude: number | null;
  longitude: number | null;
  source: string;
  notes: string | null;
}

export interface LeaveRequest {
  id: string;
  employee_id: string;
  start_date: string;
  end_date: string;
  days_requested: number;
  status: LeaveStatus;
  reason: string | null;
  supervisor_id: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
}

export interface ShiftConfiguration {
  id: string;
  name: string;
  pattern_type: ShiftPatternType;
  description: string | null;
  weekly_hours: number | null;
  pattern_definition: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface ShiftAssignment {
  id: string;
  employee_id: string;
  shift_configuration_id: string;
  valid_from: string;
  valid_to: string | null;
  calendar_overrides: Record<string, unknown>;
  created_at: string;
}

export interface DocumentDelivery {
  id: string;
  employee_id: string;
  file_path: string;
  file_name: string;
  document_type: string;
  sent_at: string | null;
  acknowledged_at: string | null;
  requires_acknowledgment: boolean;
  created_at: string;
}

export interface SystemSettings {
  gowa_send_url: string;
  gowa_basic_auth: string;
  gowa_webhook_url: string;
  gowa_ui_url: string;
  ollama_base_url: string;
  ollama_model: string;
  company_name: string;
  updated_at: string;
}

export interface ConnectionTest {
  ok: boolean;
  message: string;
  detail: string | null;
}

export interface MailSettings {
  smtp_host: string | null;
  smtp_port: number;
  smtp_user: string | null;
  smtp_use_tls: boolean;
  mail_from_address: string | null;
  mail_from_name: string | null;
  smtp_password_configured: boolean;
  updated_at: string;
}

export interface MailLog {
  id: string;
  to_address: string;
  subject: string;
  event_type: string;
  success: boolean;
  detail: string | null;
  tenant_id: string | null;
  envelope_id: string | null;
  created_at: string;
}
