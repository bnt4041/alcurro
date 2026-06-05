export type Role =
  | "employee"
  | "manager"
  | "tenant_admin"
  | "labor_inspector"
  | "supervisor"
  | "admin";

export type UserScope = "tenant" | "platform";
export type BreakType = "inicio_parada" | "fin_parada";
export type LeaveStatus = "pending" | "approved" | "rejected" | "cancelled";
export type ShiftPatternType =
  | "rigid"
  | "rotating"
  | "split"
  | "night"
  | "mixed";

export interface EmployeeBulkScheduleResult {
  updated: number;
  skipped: number;
  errors: { employee_id: string; employee_name: string | null; message: string }[];
}

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

export interface InboundDocumentType {
  code: string;
  name: string;
  description: string;
  optional?: boolean;
  kind?: string;
}

export interface CompanySignatureDocument {
  id: string;
  company_id: string | null;
  company_name: string | null;
  title: string;
  file_name: string;
  document_type: string;
}

export interface EmployeeInboundDocument {
  id: string;
  employee_id: string;
  document_code: string;
  document_name: string;
  status: string;
  document_delivery_id: string | null;
  signature_envelope_id: string | null;
  received_at: string | null;
  created_at: string;
}

export interface ClockSettings {
  tenant_id: string;
  require_geolocation: boolean;
  clock_reminder_minutes: number | null;
  incident_reminder_enabled: boolean;
  incident_reminder_minutes: number | null;
  inbound_documents_enabled: boolean;
  inbound_document_codes: string[];
  inbound_signature_delivery_ids: string[];
  send_welcome_with_documents: boolean;
  welcome_message_extra: string | null;
  daily_summary_enabled: boolean;
  require_project_on_clock_in: boolean;
  updated_at: string;
  available_inbound_types: InboundDocumentType[];
  company_signature_documents: CompanySignatureDocument[];
}

export interface Project {
  id: string;
  company_id: string;
  name: string;
  code: string;
  address: string | null;
  planned_hours: number | null;
  is_active: boolean;
  active_for_clock: boolean;
  created_at: string;
  updated_at: string;
}

export interface IncidentAutoRule {
  tenant_id: string;
  late_entrada_enabled: boolean;
  late_entrada_grace_minutes: number;
  late_entrada_notify_whatsapp: boolean;
  late_entrada_require_justification: boolean;
  updated_at: string;
}

export interface Incident {
  id: string;
  tenant_id: string;
  employee_id: string;
  employee_name?: string | null;
  category: "fichaje" | "vacaciones" | "permiso";
  incident_type: string;
  status: string;
  source: string;
  title: string;
  description: string | null;
  clock_in_id: string | null;
  leave_request_id: string | null;
  minutes_late: number | null;
  original_data: Record<string, unknown>;
  modified_data: Record<string, unknown> | null;
  employee_justification: string | null;
  internal_notes: string | null;
  public_token: string | null;
  justify_url: string | null;
  whatsapp_notified_at: string | null;
  justified_at: string | null;
  resolved_at: string | null;
  resolved_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportTimelineItem {
  time_label: string;
  kind: string;
  label: string;
  detail: string | null;
}

export interface EmployeeDayReport {
  employee_id: string;
  employee_name: string;
  report_date: string;
  timeline: ReportTimelineItem[];
  worked_minutes: number;
  break_minutes: number;
  open_clock: boolean;
  open_break: boolean;
  text_summary: string;
}

export interface ClockReminderRunResult {
  sent: number;
  skipped: number;
  errors: string[];
}

export interface ClockIn {
  id: string;
  employee_id: string;
  entrada_at: string;
  salida_at: string | null;
  latitude: number | null;
  longitude: number | null;
  source: string;
  notes: string | null;
  work_summary: string | null;
  project_id?: string | null;
  project_name?: string | null;
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

export interface DocumentType {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
}

export interface DocumentTag {
  id: string;
  tenant_id: string;
  name: string;
  color: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DocumentDelivery {
  id: string;
  tenant_id: string;
  company_id: string | null;
  employee_id: string | null;
  document_type_id: string | null;
  document_type: string;
  document_type_name: string | null;
  file_path: string;
  file_name: string;
  title: string | null;
  expires_at: string | null;
  is_expired: boolean;
  tag_ids: string[];
  tags: DocumentTag[];
  sent_at: string | null;
  acknowledged_at: string | null;
  acknowledgment_text: string | null;
  requires_acknowledgment: boolean;
  created_at: string;
}

export interface BulkPayrollItemResult {
  source_file: string;
  page: number | null;
  id_document: string | null;
  employee_id: string | null;
  employee_name: string | null;
  status: string;
  document_id: string | null;
  message: string | null;
}

export interface BulkPayrollResponse {
  total_files: number;
  total_pages: number;
  assigned: number;
  skipped: number;
  errors: number;
  items: BulkPayrollItemResult[];
}

export interface DocumentNotificationSettings {
  tenant_id: string;
  enabled: boolean;
  days_before: number[];
  channel_whatsapp: boolean;
  channel_email: boolean;
  notify_employee: boolean;
  notify_managers: boolean;
  extra_emails: string[];
  updated_at: string;
}

export interface ExpiryNotificationRunResult {
  checked: number;
  sent: number;
  skipped: number;
  errors: number;
  details: string[];
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
