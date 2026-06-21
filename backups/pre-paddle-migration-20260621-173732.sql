--
-- PostgreSQL database dump
--

\restrict r81FeeZUbeVzE0GxxSjDQpkajmY1rvLdfbgFY2pytIluticK8FXk74oVLWAh1lc

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: billingmethodtype; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.billingmethodtype AS ENUM (
    'BANK_TRANSFER',
    'CARD',
    'SEPA',
    'OTHER'
);


ALTER TYPE public.billingmethodtype OWNER TO hrm;

--
-- Name: breaktype; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.breaktype AS ENUM (
    'INICIO',
    'FIN'
);


ALTER TYPE public.breaktype OWNER TO hrm;

--
-- Name: clockintype; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.clockintype AS ENUM (
    'ENTRADA',
    'SALIDA'
);


ALTER TYPE public.clockintype OWNER TO hrm;

--
-- Name: discounttype; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.discounttype AS ENUM (
    'PERCENT',
    'FIXED'
);


ALTER TYPE public.discounttype OWNER TO hrm;

--
-- Name: gowastatus; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.gowastatus AS ENUM (
    'PENDING',
    'PROVISIONING',
    'RUNNING',
    'STOPPED',
    'ERROR'
);


ALTER TYPE public.gowastatus OWNER TO hrm;

--
-- Name: invoicestatus; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.invoicestatus AS ENUM (
    'DRAFT',
    'SENT',
    'PAID',
    'CANCELLED',
    'CREDIT_NOTE'
);


ALTER TYPE public.invoicestatus OWNER TO hrm;

--
-- Name: leavestatus; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.leavestatus AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'CANCELLED'
);


ALTER TYPE public.leavestatus OWNER TO hrm;

--
-- Name: lspaymentstatus; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.lspaymentstatus AS ENUM (
    'PENDING',
    'PAID',
    'FAILED',
    'REFUNDED'
);


ALTER TYPE public.lspaymentstatus OWNER TO hrm;

--
-- Name: pendingsignupstatus; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.pendingsignupstatus AS ENUM (
    'PENDING',
    'ACTIVE',
    'FAILED'
);


ALTER TYPE public.pendingsignupstatus OWNER TO hrm;

--
-- Name: role; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.role AS ENUM (
    'EMPLOYEE',
    'SUPERVISOR',
    'ADMIN',
    'LABOR_INSPECTOR',
    'tenant_admin',
    'manager'
);


ALTER TYPE public.role OWNER TO hrm;

--
-- Name: shiftpatterntype; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.shiftpatterntype AS ENUM (
    'RIGID',
    'ROTATING',
    'SPLIT',
    'NIGHT',
    'MIXED'
);


ALTER TYPE public.shiftpatterntype OWNER TO hrm;

--
-- Name: stripepaymentstatus; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.stripepaymentstatus AS ENUM (
    'PENDING',
    'SUCCEEDED',
    'FAILED',
    'REFUNDED'
);


ALTER TYPE public.stripepaymentstatus OWNER TO hrm;

--
-- Name: subscriptionstatus; Type: TYPE; Schema: public; Owner: hrm
--

CREATE TYPE public.subscriptionstatus AS ENUM (
    'ACTIVE',
    'TRIALING',
    'CANCELLED',
    'PAST_DUE'
);


ALTER TYPE public.subscriptionstatus OWNER TO hrm;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_actions; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.ai_actions (
    id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500),
    category character varying(50) NOT NULL,
    sort_order integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.ai_actions OWNER TO hrm;

--
-- Name: ai_conversation_rules; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.ai_conversation_rules (
    id uuid NOT NULL,
    title character varying(120) NOT NULL,
    content character varying(4000) NOT NULL,
    priority integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.ai_conversation_rules OWNER TO hrm;

--
-- Name: ai_profile_actions; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.ai_profile_actions (
    id uuid NOT NULL,
    action_id uuid NOT NULL,
    profile_key character varying(50) NOT NULL,
    enabled boolean NOT NULL
);


ALTER TABLE public.ai_profile_actions OWNER TO hrm;

--
-- Name: ai_usage_records; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.ai_usage_records (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    profile_key character varying(50),
    action_code character varying(50),
    source character varying(40) NOT NULL,
    model character varying(80) NOT NULL,
    prompt_tokens integer NOT NULL,
    completion_tokens integer NOT NULL,
    total_tokens integer NOT NULL,
    duration_ms integer NOT NULL,
    success boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.ai_usage_records OWNER TO hrm;

--
-- Name: ai_whatsapp_messages; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.ai_whatsapp_messages (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    employee_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content character varying(4000) NOT NULL,
    intent_code character varying(50),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.ai_whatsapp_messages OWNER TO hrm;

--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.api_keys (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    key_prefix character varying(24) NOT NULL,
    key_hash character varying(64) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    last_used_at timestamp without time zone,
    created_by_id uuid
);


ALTER TABLE public.api_keys OWNER TO hrm;

--
-- Name: billing_methods; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.billing_methods (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    company_id uuid,
    label character varying(120) NOT NULL,
    method_type public.billingmethodtype NOT NULL,
    is_default boolean NOT NULL,
    holder_name character varying(200),
    iban_masked character varying(40),
    card_brand character varying(30),
    card_last4 character varying(4),
    notes character varying(500),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.billing_methods OWNER TO hrm;

--
-- Name: clock_ins; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.clock_ins (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    latitude double precision,
    longitude double precision,
    source character varying(50) NOT NULL,
    notes character varying(500),
    whatsapp_message_id character varying(100),
    project_id uuid,
    entrada_at timestamp with time zone NOT NULL,
    salida_at timestamp with time zone,
    work_summary text,
    address character varying(500),
    latitude_out double precision,
    longitude_out double precision,
    address_out character varying(500)
);


ALTER TABLE public.clock_ins OWNER TO hrm;

--
-- Name: clock_pending_fichajes; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.clock_pending_fichajes (
    employee_id uuid NOT NULL,
    record_type character varying(20) NOT NULL,
    latitude double precision,
    longitude double precision,
    whatsapp_message_id character varying(100),
    created_at timestamp without time zone NOT NULL,
    pending_confirmation boolean DEFAULT false NOT NULL,
    pending_intent character varying(50),
    pending_meta json
);


ALTER TABLE public.clock_pending_fichajes OWNER TO hrm;

--
-- Name: clock_settings; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.clock_settings (
    tenant_id uuid NOT NULL,
    require_geolocation boolean NOT NULL,
    clock_reminder_minutes integer,
    incident_reminder_enabled boolean NOT NULL,
    incident_reminder_minutes integer,
    inbound_documents_enabled boolean NOT NULL,
    inbound_document_codes json NOT NULL,
    inbound_signature_delivery_ids json NOT NULL,
    send_welcome_with_documents boolean NOT NULL,
    welcome_message_extra character varying(1000),
    daily_summary_enabled boolean NOT NULL,
    require_project_on_clock_in boolean NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    clock_exit_reminder_minutes integer
);


ALTER TABLE public.clock_settings OWNER TO hrm;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.companies (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    tax_id character varying(50),
    is_active boolean NOT NULL,
    legal_name character varying(200),
    billing_email character varying(255),
    billing_phone character varying(30),
    billing_address character varying(300),
    billing_city character varying(100),
    billing_postal_code character varying(20),
    billing_province character varying(100),
    billing_country character varying(2) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.companies OWNER TO hrm;

--
-- Name: departments; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.departments (
    id uuid NOT NULL,
    work_center_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    code character varying(50) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.departments OWNER TO hrm;

--
-- Name: discounts; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.discounts (
    id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500),
    discount_type public.discounttype NOT NULL,
    value integer NOT NULL,
    valid_from date NOT NULL,
    valid_until date NOT NULL,
    pricing_plan_id uuid,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    ls_discount_id character varying(80)
);


ALTER TABLE public.discounts OWNER TO hrm;

--
-- Name: document_deliveries; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.document_deliveries (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    company_id uuid,
    employee_id uuid,
    document_type_id uuid,
    file_path character varying(500) NOT NULL,
    file_name character varying(255) NOT NULL,
    document_type character varying(50) NOT NULL,
    title character varying(255),
    expires_at date,
    sent_at timestamp without time zone,
    acknowledged_at timestamp without time zone,
    acknowledgment_text character varying(100),
    requires_acknowledgment boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.document_deliveries OWNER TO hrm;

--
-- Name: document_delivery_tags; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.document_delivery_tags (
    id uuid NOT NULL,
    document_delivery_id uuid NOT NULL,
    tag_id uuid NOT NULL
);


ALTER TABLE public.document_delivery_tags OWNER TO hrm;

--
-- Name: document_expiry_notification_logs; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.document_expiry_notification_logs (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    document_delivery_id uuid NOT NULL,
    days_before integer NOT NULL,
    channel character varying(20) NOT NULL,
    recipient character varying(255) NOT NULL,
    success boolean NOT NULL,
    detail character varying(500),
    sent_at timestamp without time zone NOT NULL
);


ALTER TABLE public.document_expiry_notification_logs OWNER TO hrm;

--
-- Name: document_notification_settings; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.document_notification_settings (
    tenant_id uuid NOT NULL,
    enabled boolean NOT NULL,
    days_before character varying(100) NOT NULL,
    channel_whatsapp boolean NOT NULL,
    channel_email boolean NOT NULL,
    notify_employee boolean NOT NULL,
    notify_managers boolean NOT NULL,
    extra_emails character varying(500),
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.document_notification_settings OWNER TO hrm;

--
-- Name: document_tags; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.document_tags (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(80) NOT NULL,
    color character varying(20),
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.document_tags OWNER TO hrm;

--
-- Name: document_types; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.document_types (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500),
    is_active boolean NOT NULL,
    sort_order integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.document_types OWNER TO hrm;

--
-- Name: employee_groups; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.employee_groups (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    group_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.employee_groups OWNER TO hrm;

--
-- Name: employee_inbound_documents; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.employee_inbound_documents (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    document_code character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    document_delivery_id uuid,
    signature_envelope_id uuid,
    received_at timestamp without time zone,
    notes character varying(500),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.employee_inbound_documents OWNER TO hrm;

--
-- Name: employee_leave_balances; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.employee_leave_balances (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    leave_type_id uuid NOT NULL,
    total_days double precision NOT NULL,
    notes character varying(500),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.employee_leave_balances OWNER TO hrm;

--
-- Name: employees; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.employees (
    id uuid NOT NULL,
    company_id uuid NOT NULL,
    department_id uuid,
    phone character varying(20) NOT NULL,
    email character varying(255),
    full_name character varying(200) NOT NULL,
    id_document character varying(20),
    employee_code character varying(50) NOT NULL,
    role public.role NOT NULL,
    supervisor_id uuid,
    vacation_days_balance double precision NOT NULL,
    is_active boolean NOT NULL,
    password_hash character varying(255),
    shift_configuration_id uuid,
    work_start_time time without time zone,
    work_end_time time without time zone,
    work_days json NOT NULL,
    work_schedule_blocks json NOT NULL,
    work_schedule_periods json NOT NULL,
    rotating_shift boolean NOT NULL,
    weekly_hours double precision,
    welcome_sent_at timestamp without time zone,
    last_clock_reminder_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    avatar_delivery_id uuid,
    job_title character varying(100),
    last_exit_reminder_at timestamp without time zone,
    last_incident_reminder_at timestamp without time zone
);


ALTER TABLE public.employees OWNER TO hrm;

--
-- Name: group_templates; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.group_templates (
    id uuid NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500),
    permissions json NOT NULL,
    is_system boolean NOT NULL,
    sort_order integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.group_templates OWNER TO hrm;

--
-- Name: inbound_pending_uploads; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.inbound_pending_uploads (
    employee_id uuid NOT NULL,
    file_path character varying(500) NOT NULL,
    filename character varying(255) NOT NULL,
    whatsapp_message_id character varying(100),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.inbound_pending_uploads OWNER TO hrm;

--
-- Name: incident_auto_rules; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.incident_auto_rules (
    tenant_id uuid NOT NULL,
    late_entrada_enabled boolean NOT NULL,
    late_entrada_grace_minutes integer NOT NULL,
    late_entrada_notify_whatsapp boolean NOT NULL,
    late_entrada_require_justification boolean NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    missing_clock_in_enabled boolean DEFAULT false NOT NULL,
    missing_clock_in_hours numeric(5,2) DEFAULT 2.0 NOT NULL,
    missing_clock_in_notify_whatsapp boolean DEFAULT true NOT NULL,
    missing_clock_in_require_justification boolean DEFAULT true NOT NULL,
    missing_clock_out_enabled boolean DEFAULT false NOT NULL,
    missing_clock_out_hours numeric(5,2) DEFAULT 12.0 NOT NULL,
    missing_clock_out_notify_whatsapp boolean DEFAULT true NOT NULL,
    missing_clock_out_require_justification boolean DEFAULT true NOT NULL
);


ALTER TABLE public.incident_auto_rules OWNER TO hrm;

--
-- Name: incident_notes; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.incident_notes (
    id uuid NOT NULL,
    incident_id uuid NOT NULL,
    author_id uuid,
    author_name character varying(200),
    content character varying(5000) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.incident_notes OWNER TO hrm;

--
-- Name: incidents; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.incidents (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    employee_id uuid NOT NULL,
    category character varying(30) NOT NULL,
    incident_type character varying(50) NOT NULL,
    status character varying(30) NOT NULL,
    source character varying(20) NOT NULL,
    title character varying(300) NOT NULL,
    description character varying(2000),
    clock_in_id uuid,
    leave_request_id uuid,
    minutes_late integer,
    original_data json NOT NULL,
    modified_data json,
    employee_justification character varying(3000),
    internal_notes character varying(2000),
    public_token character varying(64),
    whatsapp_notified_at timestamp without time zone,
    justified_at timestamp without time zone,
    resolved_at timestamp without time zone,
    resolved_by_id uuid,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    created_by_id uuid,
    managed boolean DEFAULT false,
    break_id uuid,
    incident_date date
);


ALTER TABLE public.incidents OWNER TO hrm;

--
-- Name: invoices; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.invoices (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    number character varying(50) NOT NULL,
    recipient_legal_name character varying(200),
    recipient_tax_id character varying(30),
    recipient_address character varying(300),
    recipient_city character varying(100),
    recipient_postal_code character varying(10),
    recipient_province character varying(100),
    recipient_country character varying(2) NOT NULL,
    recipient_email character varying(200),
    concept character varying(500) NOT NULL,
    base_cents integer NOT NULL,
    vat_rate integer NOT NULL,
    vat_cents integer NOT NULL,
    total_cents integer NOT NULL,
    currency character varying(3) NOT NULL,
    issue_date date NOT NULL,
    due_date date,
    status public.invoicestatus NOT NULL,
    stripe_payment_id uuid,
    credit_note_for_id uuid,
    pdf_url character varying,
    email_sent_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    ls_payment_id uuid
);


ALTER TABLE public.invoices OWNER TO hrm;

--
-- Name: leave_requests; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.leave_requests (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    days_requested double precision NOT NULL,
    status public.leavestatus NOT NULL,
    reason character varying(1000),
    supervisor_id uuid,
    reviewed_at timestamp without time zone,
    review_notes character varying(500),
    created_at timestamp without time zone NOT NULL,
    raw_message character varying,
    leave_type_id uuid
);


ALTER TABLE public.leave_requests OWNER TO hrm;

--
-- Name: leave_types; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.leave_types (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    deducts_balance boolean NOT NULL,
    is_default boolean NOT NULL,
    is_active boolean NOT NULL,
    sort_order integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    has_own_balance boolean DEFAULT false NOT NULL,
    default_days double precision
);


ALTER TABLE public.leave_types OWNER TO hrm;

--
-- Name: legal_acceptances; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.legal_acceptances (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    legal_document_id uuid NOT NULL,
    document_version integer NOT NULL,
    accepted_at timestamp without time zone NOT NULL,
    channel character varying(20) DEFAULT 'web'::character varying NOT NULL
);


ALTER TABLE public.legal_acceptances OWNER TO hrm;

--
-- Name: legal_documents; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.legal_documents (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    title character varying(200) NOT NULL,
    body character varying NOT NULL,
    version integer NOT NULL,
    is_active boolean NOT NULL,
    is_required boolean NOT NULL,
    sort_order integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.legal_documents OWNER TO hrm;

--
-- Name: legal_tokens; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.legal_tokens (
    id uuid NOT NULL,
    token character varying(64) NOT NULL,
    employee_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.legal_tokens OWNER TO hrm;

--
-- Name: ls_payments; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.ls_payments (
    id uuid NOT NULL,
    tenant_id uuid,
    subscription_id uuid,
    ls_order_id character varying(80),
    ls_subscription_id character varying(80),
    ls_invoice_id character varying(80),
    amount_cents integer NOT NULL,
    currency character varying(3) NOT NULL,
    status public.lspaymentstatus NOT NULL,
    description character varying(500),
    invoice_number character varying(50),
    receipt_url character varying,
    paid_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.ls_payments OWNER TO hrm;

--
-- Name: mail_logs; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.mail_logs (
    id uuid NOT NULL,
    to_address character varying(255) NOT NULL,
    subject character varying(500) NOT NULL,
    event_type character varying(50) NOT NULL,
    success boolean NOT NULL,
    detail character varying(1000),
    tenant_id uuid,
    envelope_id uuid,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.mail_logs OWNER TO hrm;

--
-- Name: notification_preferences; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.notification_preferences (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    event_type character varying(50) NOT NULL,
    channel character varying(20) NOT NULL,
    enabled boolean NOT NULL
);


ALTER TABLE public.notification_preferences OWNER TO hrm;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.notifications (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    employee_id uuid NOT NULL,
    event_type character varying(50) NOT NULL,
    title character varying(200) NOT NULL,
    body character varying(1000) NOT NULL,
    link character varying(500),
    actor_name character varying(200),
    read_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.notifications OWNER TO hrm;

--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.password_reset_tokens (
    id uuid NOT NULL,
    token character varying(64) NOT NULL,
    employee_id uuid NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.password_reset_tokens OWNER TO hrm;

--
-- Name: pending_signups; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.pending_signups (
    id uuid NOT NULL,
    data_json character varying NOT NULL,
    tenant_id uuid,
    ls_subscription_id character varying(80),
    status public.pendingsignupstatus NOT NULL,
    error_message character varying(500),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.pending_signups OWNER TO hrm;

--
-- Name: platform_policies; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.platform_policies (
    id uuid NOT NULL,
    ai_monthly_limit integer NOT NULL,
    ai_limit_action character varying(20) NOT NULL,
    whatsapp_monthly_limit integer NOT NULL,
    whatsapp_limit_action character varying(20) NOT NULL,
    support_channel character varying(50) NOT NULL,
    support_email character varying(200),
    support_notice character varying(1000),
    tos_notice character varying(2000),
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.platform_policies OWNER TO hrm;

--
-- Name: platform_settings; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.platform_settings (
    id uuid NOT NULL,
    legal_name character varying(200) NOT NULL,
    tax_id character varying(30) NOT NULL,
    billing_address character varying(300),
    billing_city character varying(100),
    billing_postal_code character varying(10),
    billing_province character varying(100),
    billing_country character varying(2) NOT NULL,
    billing_email character varying(200),
    billing_phone character varying(30),
    website character varying(200),
    iban character varying(40),
    bank_name character varying(200),
    swift_bic character varying(20),
    invoice_prefix character varying(10) NOT NULL,
    invoice_next_number integer NOT NULL,
    invoice_current_year integer NOT NULL,
    vat_rate integer NOT NULL,
    invoice_footer_text character varying(500),
    auto_send_invoice_email boolean NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    credit_note_prefix character varying(10) DEFAULT 'ALC-R'::character varying,
    credit_note_next_number integer DEFAULT 1,
    credit_note_current_year integer DEFAULT 2026
);


ALTER TABLE public.platform_settings OWNER TO hrm;

--
-- Name: platform_users; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.platform_users (
    id uuid NOT NULL,
    email character varying(255) NOT NULL,
    full_name character varying(200) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.platform_users OWNER TO hrm;

--
-- Name: pricing_plans; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.pricing_plans (
    id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500),
    monthly_price_cents integer NOT NULL,
    annual_price_cents integer NOT NULL,
    max_active_users integer NOT NULL,
    currency character varying(3) NOT NULL,
    is_active boolean NOT NULL,
    sort_order integer NOT NULL,
    stripe_product_id character varying(120),
    stripe_price_monthly_id character varying(120),
    stripe_price_annual_id character varying(120),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    ls_variant_id_monthly character varying(80),
    ls_variant_id_annual character varying(80),
    ls_product_id character varying(80)
);


ALTER TABLE public.pricing_plans OWNER TO hrm;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.projects (
    id uuid NOT NULL,
    company_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    code character varying(50) NOT NULL,
    address character varying(500),
    planned_hours double precision,
    is_active boolean NOT NULL,
    active_for_clock boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.projects OWNER TO hrm;

--
-- Name: shift_assignments; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.shift_assignments (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    shift_configuration_id uuid NOT NULL,
    valid_from date NOT NULL,
    valid_to date,
    calendar_overrides json NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.shift_assignments OWNER TO hrm;

--
-- Name: shift_configurations; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.shift_configurations (
    id uuid NOT NULL,
    company_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    pattern_type public.shiftpatterntype NOT NULL,
    description character varying(500),
    weekly_hours double precision,
    pattern_definition json NOT NULL,
    default_start_time time without time zone,
    default_end_time time without time zone,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.shift_configurations OWNER TO hrm;

--
-- Name: signature_envelopes; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.signature_envelopes (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    document_delivery_id uuid,
    reference character varying(32) NOT NULL,
    title character varying(255) NOT NULL,
    status character varying(20) NOT NULL,
    original_path character varying(500) NOT NULL,
    original_hash character varying(64) NOT NULL,
    signed_path character varying(500),
    signed_hash character varying(64),
    certificate_path character varying(500),
    certificate_json_path character varying(500),
    expires_at timestamp without time zone,
    completed_at timestamp without time zone,
    cancelled_at timestamp without time zone,
    cancel_reason character varying(500),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.signature_envelopes OWNER TO hrm;

--
-- Name: signature_events; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.signature_events (
    id uuid NOT NULL,
    envelope_id uuid NOT NULL,
    event_type character varying(50) NOT NULL,
    payload_json character varying NOT NULL,
    prev_hash character varying(64),
    event_hash character varying(64) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.signature_events OWNER TO hrm;

--
-- Name: signature_notifications; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.signature_notifications (
    id uuid NOT NULL,
    envelope_id uuid NOT NULL,
    signer_id uuid,
    channel character varying(20) NOT NULL,
    event_type character varying(30) NOT NULL,
    success boolean NOT NULL,
    detail character varying(500),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.signature_notifications OWNER TO hrm;

--
-- Name: signature_otps; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.signature_otps (
    id uuid NOT NULL,
    signer_id uuid NOT NULL,
    code_hash character varying(64) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    attempts integer NOT NULL,
    used_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.signature_otps OWNER TO hrm;

--
-- Name: signature_signers; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.signature_signers (
    id uuid NOT NULL,
    envelope_id uuid NOT NULL,
    employee_id uuid,
    full_name character varying(200) NOT NULL,
    email character varying(255),
    phone character varying(30),
    id_document character varying(20) NOT NULL,
    sign_order integer NOT NULL,
    status character varying(20) NOT NULL,
    token_hash character varying(64) NOT NULL,
    token_plain character varying(64),
    otp_verified_at timestamp without time zone,
    signed_at timestamp without time zone,
    signature_path character varying(500),
    signer_name character varying(200),
    ip_address character varying(45),
    user_agent character varying(500),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.signature_signers OWNER TO hrm;

--
-- Name: stripe_payments; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.stripe_payments (
    id uuid NOT NULL,
    tenant_id uuid,
    subscription_id uuid,
    stripe_payment_intent_id character varying(120),
    stripe_invoice_id character varying(120),
    stripe_checkout_session_id character varying(120),
    amount_cents integer NOT NULL,
    currency character varying(3) NOT NULL,
    status public.stripepaymentstatus NOT NULL,
    description character varying(500),
    paid_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    invoice_pdf_url text,
    invoice_url text,
    invoice_number character varying(50)
);


ALTER TABLE public.stripe_payments OWNER TO hrm;

--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.subscriptions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    company_id uuid,
    pricing_plan_id uuid,
    discount_id uuid,
    plan_code character varying(50) NOT NULL,
    plan_name character varying(120) NOT NULL,
    status public.subscriptionstatus NOT NULL,
    amount_cents integer NOT NULL,
    currency character varying(3) NOT NULL,
    billing_cycle character varying(20) NOT NULL,
    billing_method_id uuid,
    current_period_start date,
    current_period_end date,
    stripe_subscription_id character varying(120),
    stripe_checkout_session_id character varying(120),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    pending_plan_id uuid,
    pending_billing_cycle character varying(20),
    ls_subscription_id character varying(80),
    payment_failure_count integer DEFAULT 0 NOT NULL,
    last_payment_failure_at timestamp without time zone
);


ALTER TABLE public.subscriptions OWNER TO hrm;

--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.system_settings (
    id integer NOT NULL,
    gowa_send_url character varying NOT NULL,
    gowa_basic_auth character varying NOT NULL,
    gowa_webhook_url character varying NOT NULL,
    gowa_ui_url character varying NOT NULL,
    gowa_device_id character varying(80),
    ollama_base_url character varying NOT NULL,
    ollama_model character varying NOT NULL,
    company_name character varying NOT NULL,
    smtp_host character varying(255),
    smtp_port integer NOT NULL,
    smtp_user character varying(255),
    smtp_password character varying(255),
    smtp_use_tls boolean NOT NULL,
    mail_from_address character varying(255),
    mail_from_name character varying,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.system_settings OWNER TO hrm;

--
-- Name: tenants; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.tenants (
    id uuid NOT NULL,
    slug character varying(80) NOT NULL,
    name character varying(200) NOT NULL,
    is_active boolean NOT NULL,
    legal_name character varying(200),
    tax_id character varying(50),
    billing_email character varying(255),
    billing_phone character varying(30),
    billing_address character varying(300),
    billing_city character varying(100),
    billing_postal_code character varying(20),
    billing_province character varying(100),
    billing_country character varying(2) NOT NULL,
    logo_url character varying(500),
    primary_color character varying(20) NOT NULL,
    secondary_color character varying(20) NOT NULL,
    accent_color character varying(20) NOT NULL,
    gowa_container_name character varying(100),
    gowa_host character varying(200) NOT NULL,
    gowa_port integer,
    gowa_send_url character varying NOT NULL,
    gowa_ui_url character varying NOT NULL,
    gowa_basic_auth character varying(100) NOT NULL,
    gowa_webhook_path character varying(200) NOT NULL,
    gowa_device_id character varying(80),
    gowa_status public.gowastatus NOT NULL,
    gowa_error character varying(500),
    ollama_base_url character varying NOT NULL,
    ollama_model character varying NOT NULL,
    stripe_customer_id character varying(120),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    billing_company_id uuid,
    ls_customer_id character varying(80),
    ls_customer_portal_url text
);


ALTER TABLE public.tenants OWNER TO hrm;

--
-- Name: user_groups; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.user_groups (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500),
    is_system boolean NOT NULL,
    permissions json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.user_groups OWNER TO hrm;

--
-- Name: webhook_deliveries; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.webhook_deliveries (
    id uuid NOT NULL,
    webhook_id uuid NOT NULL,
    event_type character varying(50) NOT NULL,
    payload json NOT NULL,
    status character varying(20) NOT NULL,
    response_status integer,
    response_body character varying(2000),
    attempts integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    delivered_at timestamp without time zone
);


ALTER TABLE public.webhook_deliveries OWNER TO hrm;

--
-- Name: webhook_endpoints; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.webhook_endpoints (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    url character varying(500) NOT NULL,
    description character varying(200),
    events json NOT NULL,
    secret character varying(64) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    last_triggered_at timestamp without time zone,
    failure_count integer NOT NULL
);


ALTER TABLE public.webhook_endpoints OWNER TO hrm;

--
-- Name: whatsapp_dedup; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.whatsapp_dedup (
    wa_msg_id character varying(200) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.whatsapp_dedup OWNER TO hrm;

--
-- Name: work_breaks; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.work_breaks (
    id uuid NOT NULL,
    employee_id uuid NOT NULL,
    record_type public.breaktype NOT NULL,
    recorded_at timestamp without time zone NOT NULL,
    source character varying(50) NOT NULL,
    notes character varying(500),
    whatsapp_message_id character varying(100),
    clock_in_id uuid NOT NULL
);


ALTER TABLE public.work_breaks OWNER TO hrm;

--
-- Name: work_centers; Type: TABLE; Schema: public; Owner: hrm
--

CREATE TABLE public.work_centers (
    id uuid NOT NULL,
    company_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    code character varying(50) NOT NULL,
    address character varying(300),
    city character varying(100),
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.work_centers OWNER TO hrm;

--
-- Data for Name: ai_actions; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.ai_actions (id, code, name, description, category, sort_order, is_active, created_at) FROM stdin;
4a49d17c-6bab-4105-bf6c-15edc6068606	fichar_entrada	Fichar entrada	Registra entrada por mensaje	fichajes	0	t	2026-05-25 18:50:56.47546
caa71eef-deba-4058-a03c-9cf80ba21936	fichar_salida	Fichar salida	Registra salida por mensaje	fichajes	1	t	2026-05-25 18:50:56.47852
1e88de49-346d-40a3-94a0-30534e118e75	inicio_parada	Inicio de parada	Inicia parada / descanso	paradas	2	t	2026-05-25 18:50:56.479972
1232def5-d835-41e1-a592-494db6804a79	fin_parada	Fin de parada	Finaliza parada / descanso	paradas	3	t	2026-05-25 18:50:56.48129
46eaba6f-546f-4bed-a24b-2340b7c422c9	solicitar_vacaciones	Solicitar vacaciones	Crea solicitud de vacaciones	vacaciones	4	t	2026-05-25 18:50:56.482561
8f61357d-33e5-4f2c-a552-c1aeec1ad4f5	consultar_saldo_vacaciones	Consultar saldo vacaciones	Informa días disponibles	vacaciones	5	t	2026-05-25 18:50:56.483901
c881e64c-e782-408c-9e88-3428021d259d	confirmar_documento	Confirmar documento	Acuse de recibo de documento	documentos	6	t	2026-05-25 18:50:56.48522
62e28b4f-742e-4b24-afe3-1f4e9092021e	resumen_dia	Resumen del día	Muestra fichajes y paradas del día actual	fichajes	7	t	2026-05-25 18:50:56.486361
a3c28673-155b-4451-a694-4a79cf27b8be	reportar_incidencia	Reportar incidencia	Registra una incidencia de fichaje (problema, retraso, avería…)	fichajes	8	t	2026-06-06 15:25:19.341442
54a94ff8-6bca-4c97-974c-7ed771dc066e	solicitar_permiso	Solicitar permiso	Registra permiso médico, personal o similar	permisos	5	t	2026-06-06 18:47:56.933621
\.


--
-- Data for Name: ai_conversation_rules; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.ai_conversation_rules (id, title, content, priority, is_active, created_at, updated_at) FROM stdin;
5c4c51dc-51b5-4cc9-852b-c192129cc1e1	Comprensión coloquial (sistema)	Interpreta español coloquial de España sin exigir frases del menú. Ejemplos: «ficho ahora»=fichar; «vuelvo al trabajo»=fin_parada si hay parada abierta; «pausa»/«a comer»=inicio_parada; «me voy»=salida de jornada. Usa historial + estado de fichaje y paradas. Nunca respondas solo con lista de comandos: si no entiendes, pregunta en una frase corta y amable.	0	t	2026-05-26 11:53:10.605536	2026-05-26 11:53:10.605555
\.


--
-- Data for Name: ai_profile_actions; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.ai_profile_actions (id, action_id, profile_key, enabled) FROM stdin;
8ad957e2-3bde-4de8-ab28-be20a53e7755	4a49d17c-6bab-4105-bf6c-15edc6068606	employee	t
be6ac258-cf88-45fa-aa99-cca72af5cfdb	caa71eef-deba-4058-a03c-9cf80ba21936	employee	t
022432ee-ddf3-4bb2-90dd-ad2ce6ad37c0	1e88de49-346d-40a3-94a0-30534e118e75	employee	t
39646016-2606-4ec6-b56a-c5f9660a242b	1232def5-d835-41e1-a592-494db6804a79	employee	t
292ea40e-8f01-46d1-bf11-fd186859153f	46eaba6f-546f-4bed-a24b-2340b7c422c9	employee	t
e51b2676-9030-4c40-a6cd-73265497c03c	8f61357d-33e5-4f2c-a552-c1aeec1ad4f5	employee	t
c6e55429-9699-4399-b6c1-aa9dc77b49a6	c881e64c-e782-408c-9e88-3428021d259d	employee	t
5d53fd15-a264-4024-9bbc-ddff56105c28	62e28b4f-742e-4b24-afe3-1f4e9092021e	employee	t
a0403ea7-7883-441d-ab29-230321ce76ec	4a49d17c-6bab-4105-bf6c-15edc6068606	manager	t
7e152d05-78c5-4bbd-8c0d-4a92e067f79e	caa71eef-deba-4058-a03c-9cf80ba21936	manager	t
efd72804-51a1-43c9-bfc7-4d4612808c57	1e88de49-346d-40a3-94a0-30534e118e75	manager	t
3977ba07-2fe0-4308-92ae-1fe97d67ff53	1232def5-d835-41e1-a592-494db6804a79	manager	t
e2855f52-923c-43f4-9849-5f9023d8a2f3	46eaba6f-546f-4bed-a24b-2340b7c422c9	manager	t
96e508a5-a4c8-460e-8484-8001c6d50ad2	8f61357d-33e5-4f2c-a552-c1aeec1ad4f5	manager	t
ea24aa76-19a9-46f1-8c92-2df87f698a06	c881e64c-e782-408c-9e88-3428021d259d	manager	t
e7504d1c-4ef3-45ef-948a-7f7ab43c2b07	62e28b4f-742e-4b24-afe3-1f4e9092021e	manager	t
4851760e-bc27-445a-b565-8ac1398e3fd9	4a49d17c-6bab-4105-bf6c-15edc6068606	tenant_admin	t
6eb24901-2e88-44e2-9dad-c92c2359fd77	caa71eef-deba-4058-a03c-9cf80ba21936	tenant_admin	t
2c761518-3127-480c-a864-2e305311acd9	1e88de49-346d-40a3-94a0-30534e118e75	tenant_admin	t
bca41df4-94e5-4963-a3fa-92eeace659ec	1232def5-d835-41e1-a592-494db6804a79	tenant_admin	t
3be61360-786c-482f-b246-be264fe30270	46eaba6f-546f-4bed-a24b-2340b7c422c9	tenant_admin	t
db432203-fad9-4e83-bb31-1f12831ab083	8f61357d-33e5-4f2c-a552-c1aeec1ad4f5	tenant_admin	t
b7548571-a2eb-4534-a151-c4a10794b72e	c881e64c-e782-408c-9e88-3428021d259d	tenant_admin	t
deb29fcd-6c30-4a2c-96cc-d628037bfeac	62e28b4f-742e-4b24-afe3-1f4e9092021e	tenant_admin	t
6f0ba193-17f5-44db-aaab-db85fa2186cb	4a49d17c-6bab-4105-bf6c-15edc6068606	labor_inspector	f
6b13a6e4-b6ec-4b54-8910-2449e2e549e3	caa71eef-deba-4058-a03c-9cf80ba21936	labor_inspector	f
ed609267-e0e5-4b7b-bd0f-0c81fc73808b	1e88de49-346d-40a3-94a0-30534e118e75	labor_inspector	f
13a0bcc6-001e-47b2-b809-a665dde3a1c8	1232def5-d835-41e1-a592-494db6804a79	labor_inspector	f
bec3605a-da20-4892-be0b-3b4d96054c6e	46eaba6f-546f-4bed-a24b-2340b7c422c9	labor_inspector	f
402a6cda-59c9-4473-a8b0-17f21ef44135	8f61357d-33e5-4f2c-a552-c1aeec1ad4f5	labor_inspector	t
73d73b32-a0fe-456c-8fb2-21159d25d343	c881e64c-e782-408c-9e88-3428021d259d	labor_inspector	f
2d4bffc7-c0f1-4fa2-9a29-449872dbb5e5	62e28b4f-742e-4b24-afe3-1f4e9092021e	labor_inspector	f
6a6d62ce-752d-4c85-a38e-d7d36ae3dd21	a3c28673-155b-4451-a694-4a79cf27b8be	employee	t
6e81d03c-4c39-4166-9539-41e54bed8ec9	a3c28673-155b-4451-a694-4a79cf27b8be	manager	t
f474030f-aace-46bc-9038-b5c91c2f1d2d	a3c28673-155b-4451-a694-4a79cf27b8be	tenant_admin	t
5742ae9f-aa23-40de-9911-13464363a23a	a3c28673-155b-4451-a694-4a79cf27b8be	labor_inspector	f
8db58136-0808-4b1a-a1f7-16a0c27964a7	54a94ff8-6bca-4c97-974c-7ed771dc066e	employee	t
6d6e618e-566c-4fa7-8c75-5cc044056729	54a94ff8-6bca-4c97-974c-7ed771dc066e	manager	t
3b9fc812-0625-4f81-a6d6-4bdb13041932	54a94ff8-6bca-4c97-974c-7ed771dc066e	tenant_admin	t
c9acc821-d1d4-485d-8600-121867eb68c0	54a94ff8-6bca-4c97-974c-7ed771dc066e	labor_inspector	f
\.


--
-- Data for Name: ai_usage_records; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.ai_usage_records (id, tenant_id, profile_key, action_code, source, model, prompt_tokens, completion_tokens, total_tokens, duration_ms, success, created_at) FROM stdin;
7081e06d-55f5-4709-8fe4-6dcc0ee029b3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2	0	0	0	128	f	2026-05-26 10:07:18.722883
9ea548e3-29dd-4533-b420-ce9639005103	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2	0	0	0	120	f	2026-05-26 10:07:35.482524
b972f7e9-102a-41d7-a161-8866a6b506e0	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2	0	0	0	154	f	2026-05-26 10:16:06.85259
8de7bcf9-bbd0-4a95-8fa3-49a7d4edc0c1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_keyword	llama3.2	0	0	0	42	t	2026-05-26 10:16:13.223272
452b40b4-d1f5-40bf-ae5e-de727a8de416	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2	0	0	0	161	f	2026-05-26 10:22:13.657363
b7404857-3a41-430b-bc45-d04f45035706	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_keyword	llama3.2	0	0	0	56	t	2026-05-26 10:22:27.102076
fba9cfc7-d72b-4868-9d3d-c4e130d7429e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2	0	0	0	122	f	2026-05-26 10:29:21.53702
171f4157-0115-4fb3-a8ea-4bfd1bf2007f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_keyword	llama3.2	0	0	0	43	t	2026-05-26 11:00:10.488784
9acf3346-44dc-44f4-a85e-6352dc087726	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2	0	0	0	133	f	2026-05-26 11:00:25.190123
0a6f6a12-2d0b-4547-a74a-3de9694f9d23	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2	0	0	0	118	f	2026-05-26 11:00:38.032275
f00e0fce-e8a5-4116-9204-8544f05bc2b4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_keyword	llama3.2	0	0	0	45	t	2026-05-26 11:00:42.744679
38d4c9e1-7bf5-4abe-9d3b-5edb3e3e429f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp_keyword	llama3.2	0	0	0	183	f	2026-05-26 11:54:45.592522
02afd4c5-81d9-4db4-9d6f-9d1f002494e9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_keyword	llama3.2	0	0	0	74	t	2026-05-26 11:54:57.860814
d6947b97-cd8e-48f7-b648-d37de8f7e671	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	126	f	2026-05-26 11:55:47.166533
6e24bf5f-f2f0-4cdd-ac5e-e33f6135e004	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp_keyword	llama3.2	0	0	0	124	f	2026-05-26 13:03:32.231777
bf303044-bb0a-4bd4-b1a3-133e54929873	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	149	f	2026-05-26 14:48:21.000058
73ebb2c3-9b83-46f8-8256-6612c8a0dabf	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	166	f	2026-05-27 05:39:34.966138
667609c5-9928-4f21-90ee-4913fd0c42eb	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	168	f	2026-05-27 05:39:51.177688
f3f35460-bf40-4876-aed8-bcab2880cb74	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	137	f	2026-05-27 05:46:33.84509
ddee0a49-b5ed-40bf-8a8c-000276fa1fa4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	165	f	2026-05-27 05:47:41.132329
5b854a3b-249b-4dd4-a40a-ae5fd094a9c2	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	124	f	2026-05-27 05:48:11.032775
252e9063-1390-4799-a304-ed94f0b975f8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	155	f	2026-05-27 05:48:12.758827
2cd97042-bb2c-44df-8042-759e7e5a11ba	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	127	f	2026-05-27 05:48:38.464067
10838827-99cd-4f3a-86c3-c7c9ffcfa922	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	177	f	2026-05-27 05:57:12.963905
97bf79ee-8ad7-4a78-8369-1752ed1490d1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	167	f	2026-05-27 06:03:13.133722
54cac128-6323-496b-b1e7-b9bc7ca43fcd	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60129	f	2026-05-27 06:06:10.584478
b3443d70-ace2-4d14-a730-e2755db1eadb	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60133	f	2026-05-27 06:06:21.622752
e144cb22-a1df-4012-8756-1635a4191e21	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60140	f	2026-05-27 06:06:33.610149
52aedad2-381a-43be-974b-a57366078222	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60145	f	2026-05-27 06:07:18.155717
ec94fd94-ea4b-4270-8e1b-8d86047c8620	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60123	f	2026-05-27 06:07:29.129253
6e4b9272-05c1-4b0a-91cc-58339ee26b3e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60124	f	2026-05-27 06:07:41.129119
f959fc0b-f5ec-40ad-afbb-cbac73751518	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60129	f	2026-05-27 06:08:43.350418
d4abef53-ed55-4842-ab38-72eeacb777dc	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60133	f	2026-05-27 06:08:54.356401
96a444eb-4807-41d1-b9ba-32e92b7ca6de	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	llama3.2	0	0	0	60122	f	2026-05-27 06:09:06.347169
bc134919-d80e-43fc-b322-2d0840f473fe	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	confirmar_documento	whatsapp	llama3.2:1b	2420	72	2492	47980	t	2026-05-27 06:11:53.998926
5a0bca19-f587-4e62-9924-dc8904adda8b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2:1b	2420	68	2488	44024	t	2026-05-27 06:12:01.035891
16f003ec-f6d0-4256-bcd5-283eb0e84715	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	llama3.2:1b	2420	44	2464	36446	t	2026-05-27 06:12:05.45797
fba5aff5-801f-4a35-8f88-aa8f1f37bcbc	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp	llama3.2:1b	2307	41	2348	14838	t	2026-05-27 06:16:18.67927
9044a8d9-003d-4df5-a234-1ea8993fa3f4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	llama3.2:1b	2307	41	2348	7808	t	2026-05-27 06:16:22.624882
69c0cc2e-129c-4610-b158-451d2f4b2960	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	llama3.2:1b	2172	46	2218	12292	t	2026-05-27 06:16:51.102095
0846e485-1199-48d4-97bd-91c96a1fe725	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	llama3.2:1b	2172	32	2204	4289	t	2026-05-27 06:16:54.103088
58710d06-e4e7-4fb3-a31e-2988db18b400	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp	llama3.2:1b	2078	64	2142	12099	t	2026-05-27 06:17:26.95452
60634728-e50e-40f3-987a-dbbf76def7bc	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp	llama3.2:1b	2078	29	2107	3851	t	2026-05-27 06:17:29.709195
31b2bec3-b9cf-4f0f-bdd5-1295b91a8c15	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	llama3.2:1b	2199	52	2251	44344	t	2026-05-27 06:23:22.966467
66a14415-1948-4012-bd4a-40f1b5d641b9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	llama3.2:1b	2199	47	2246	37971	t	2026-05-27 06:23:27.602864
81a048b3-95e0-446d-a38c-d885b6843fb5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	llama3.2:1b	2194	47	2241	12807	t	2026-05-27 06:23:58.048098
d76e7623-1503-45b4-9afa-5ce7983f7195	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	1071	21	1092	23463	t	2026-05-27 06:31:04.090371
aeef2031-6630-4fa8-b7ce-a4a3278256ee	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	1071	21	1092	13913	t	2026-05-27 06:31:05.54543
46d6d668-6835-4eca-8fbc-925d1c756150	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1041	50	1091	26536	t	2026-05-27 06:39:47.740482
22cf5f69-2387-45cb-80c9-f4df9bd49826	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1031	42	1073	16153	t	2026-05-27 06:42:35.454973
54d0ed49-e6de-411d-8eb1-4d05ba205b4e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1096	40	1136	11789	t	2026-05-27 06:42:47.264247
e8b1060f-601f-4782-8e5c-24bcf3654ff7	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1129	43	1172	28473	t	2026-05-27 19:06:16.262083
01233c47-acfa-408c-a9fc-9e395614f0e2	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1129	43	1172	20596	t	2026-05-27 19:06:19.385211
99d3c4cf-0f9b-4142-91d4-2e0f1bae16a7	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1026	43	1069	26035	t	2026-05-27 19:16:31.582514
f27994e9-fbdb-4db9-90c5-8826a13b4a1e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	resumen_dia	whatsapp	qwen2.5:1.5b	1014	41	1055	25337	t	2026-05-27 19:29:54.48027
825b01ae-1189-4d22-a1c2-86565b6c2e8f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp	qwen2.5:1.5b	1014	42	1056	25343	t	2026-05-27 19:29:57.740871
685fcec3-517b-4770-aa55-659c76f79854	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	resumen_dia	whatsapp	qwen2.5:1.5b	1014	41	1055	20732	t	2026-05-27 19:30:00.847826
0a5384e7-a05b-4d54-b798-b2f5ff3b91f2	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1209	35	1244	29172	t	2026-05-28 05:25:24.780638
5c4e7a7c-2517-4c3d-b750-2c6a6400cf97	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1214	47	1261	15725	t	2026-05-28 05:26:27.095437
ea55010f-565b-4467-a3bd-506e5dc456fa	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1214	67	1281	9315	t	2026-05-28 05:26:31.687297
4c8cc84b-563f-4aa5-a32f-6ccab66b3532	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	0	0	0	10203	t	2026-05-28 05:38:39.712914
cd082ac3-ef18-4cec-afc4-c64b79fc5ddc	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1081	38	1119	18346	t	2026-05-28 06:14:52.896877
cef7afaf-c363-478f-8fb6-15f79d139105	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	1314	38	1352	17599	t	2026-05-28 05:28:05.644344
9005bd09-577e-463d-b8f1-3d3d24c1b705	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	1314	38	1352	9413	t	2026-05-28 05:28:08.463092
b227f46e-150b-4745-b19d-11cceee5d335	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	1113	48	1161	10197	t	2026-05-28 05:28:34.684716
510051c4-2c2c-489c-851b-50699e3e68f3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	1218	54	1272	31120	t	2026-05-28 06:00:27.495874
82a7b2ce-fae5-4e56-b72b-d10ef4b37948	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1218	42	1260	26459	t	2026-05-28 06:00:34.261832
0976793d-ef96-4787-ae13-566533977a98	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	993	39	1032	10127	t	2026-05-28 05:28:45.613107
b62dab63-bdc8-42d0-b6d8-766eb13315c8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	986	47	1033	25070	t	2026-05-28 05:36:57.422469
b133f645-4e14-4819-9f86-19e81538bac9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	932	32	964	7894	t	2026-05-28 05:37:55.824929
ac5c32b0-9541-4e9b-8d3a-09f87145b1cb	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	1218	46	1264	23548	t	2026-05-28 06:00:30.926112
c2c9416e-a9e2-470b-b6bf-aed6b4357027	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1102	50	1152	27618	t	2026-05-28 06:14:50.031437
1ce48820-baad-4143-a32c-1a3064af38de	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1398	54	1452	37049	t	2026-05-28 15:55:58.842209
8a3f59e3-7efc-4c85-a3e0-811d685a51c7	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	1481	37	1518	36738	t	2026-05-28 16:22:33.54852
d1fd34b8-7155-4062-bd14-77bd05f3343e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	1487	35	1522	11123	t	2026-05-28 16:23:04.916737
00291d35-8ed9-4e5a-bf49-6deb02694337	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fin_parada	whatsapp_keyword	qwen2.5:1.5b	0	0	0	53	t	2026-05-28 18:05:25.785861
0556776c-cac4-43be-8329-e7753d4568d8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp	qwen2.5:1.5b	1573	18	1591	36888	t	2026-05-28 18:06:25.749018
3d21f16b-cdc5-45fc-a218-2b24154d0a65	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp	qwen2.5:1.5b	1573	18	1591	27223	t	2026-05-28 18:06:27.093979
1ee1becf-5403-4027-b7f8-6b21ababf7a4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp	qwen2.5:1.5b	1573	17	1590	16539	t	2026-05-28 18:06:28.404278
8e70d1bc-0920-431a-9ca5-b618e3210bc7	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp	qwen2.5:1.5b	1433	18	1451	33833	t	2026-05-29 06:31:41.471918
6eea18ce-f8d4-40f2-9771-eca02ffc9bc9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp	qwen2.5:1.5b	1433	18	1451	24196	t	2026-05-29 06:31:42.841139
06874629-220b-4080-9317-1fa5ccb92d8a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp	qwen2.5:1.5b	1433	40	1473	15054	t	2026-05-29 06:31:45.68899
a35edddf-29ab-405c-9f9c-66089cbcf6d6	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1408	55	1463	35512	t	2026-05-29 07:23:42.86095
70e55f9d-8c2f-46bb-8442-65d6fa14c36f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1398	36	1434	8270	t	2026-05-29 07:24:06.730451
65324772-8480-4795-88d7-891a6727f261	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp	qwen2.5:1.5b	1447	35	1482	35416	t	2026-05-29 08:08:49.510367
e6d9ed90-909a-4cf0-b50b-07b34a587384	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1493	48	1541	37409	t	2026-05-29 20:10:25.057817
3f4287c2-ebb9-4696-9b5f-d406f2157f24	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1480	58	1538	11784	t	2026-05-29 20:10:48.59228
08e36b0e-cc06-4cd4-9037-22a250eabdc5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	1492	59	1551	18522	t	2026-05-29 20:11:17.413613
17e87571-ed8f-4d02-b010-a05c68ff59c5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1515	54	1569	38649	t	2026-05-30 14:28:13.922046
e6f4fad8-7bea-4278-9c54-4fc4ea939923	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	1512	15	1527	35275	t	2026-05-30 14:34:15.85752
65a46b85-5b6c-49e0-b6e5-f34df2356453	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	2209	53	2262	57856	t	2026-05-30 14:56:59.498631
f8218141-4983-4f50-9ded-dad0a80580b0	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:1.5b	0	0	0	60155	f	2026-05-30 15:04:24.255322
18529614-ae56-40ed-a8fc-c13dd7028f4b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:1.5b	0	0	0	60147	f	2026-05-30 15:05:45.57041
ea0df26c-f040-4b61-8f4e-85472673e309	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	2510	54	2564	38072	t	2026-05-30 15:09:40.84701
c78b21f7-cc5b-4046-87c9-e56128c89cff	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:1.5b	0	0	0	60149	f	2026-05-30 15:26:38.042283
6eabf44a-7f93-400e-afa1-35db0d05805f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	2454	54	2508	12108	t	2026-05-30 15:27:00.367951
2615219f-5ac7-4ef6-a651-3aa489569b57	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp	qwen2.5:1.5b	936	38	974	22315	t	2026-05-30 15:30:03.458043
a4c04d11-0564-4b34-bcfd-592d077c5c24	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	926	43	969	5130	t	2026-05-30 15:30:27.107242
d7c8b867-3c62-4c89-83ae-1f1e39f64b13	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	940	43	983	23778	t	2026-05-30 15:49:19.588909
9a2d9a57-981e-402e-b3f0-7e16d4e7f713	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	0	0	0	53	t	2026-05-30 17:36:40.269803
a034cbc9-8302-41fe-bc36-446ae9e165af	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp	qwen2.5:1.5b	968	51	1019	25202	t	2026-05-30 17:37:24.687606
943daeca-7c21-4146-95a3-e8fa62c87091	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp	qwen2.5:1.5b	961	43	1004	6009	t	2026-05-30 17:37:47.791297
f08a08ad-5113-4c76-aa9e-c65036808ee1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	1006	37	1043	25267	t	2026-05-30 17:52:18.595709
ad7c5a13-7000-4fdd-ad53-11ad6b40b850	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp	qwen2.5:1.5b	0	0	0	45	t	2026-05-30 17:53:58.168752
c6663fa6-1101-434c-a605-945f55ac8ac9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_fallback	qwen2.5:7b	0	0	0	60139	f	2026-05-30 18:23:01.992806
b921ba21-bfb9-46bf-8ce1-c75524b1fcac	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp_fallback	qwen2.5:7b	0	0	0	60108	f	2026-05-30 18:29:55.296568
9bf304c0-b4fd-4af1-a3ae-7461be802d14	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	1568005	f	2026-05-30 18:58:59.796914
840f509b-1ad2-4250-8fc3-4bad91981522	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	60113	f	2026-05-31 09:07:52.762545
abf97855-3489-41f8-a252-1c1ee90d44c0	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	qwen2.5:7b	1010	39	1049	48764	t	2026-05-31 09:11:41.079327
d36ad15a-1a06-4cc4-bc83-8acd40ca827f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	qwen2.5:7b	1007	33	1040	19078	t	2026-05-31 09:12:43.820022
a7f9429e-cf58-48a7-83b9-ef7f75f45f3c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_fallback	qwen2.5:7b	0	0	0	2449334	f	2026-05-31 09:59:30.642786
c84a2be8-b49a-4157-af29-121b7de808c4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:7b	0	0	0	60176	f	2026-06-04 13:19:05.540775
6e2914f3-35fa-4cf2-9606-0154a0caec7e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:7b	0	0	0	60150	f	2026-06-04 13:33:52.686734
920d69da-2ef9-4b85-a9c8-2dc1e2fc8ffd	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:7b	0	0	0	60113	f	2026-06-04 13:35:19.457064
be24b177-1290-4842-bd05-53c4257fc9a1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:7b	0	0	0	60113	f	2026-06-04 13:35:26.241037
ae1e58d5-db1f-4ae4-a88a-c7dfb48143a2	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:7b	0	0	0	60132	f	2026-06-04 13:42:10.296079
f5210c82-bbef-46d6-8e85-49e6fdd1b265	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_keyword	qwen2.5:7b	0	0	0	60172	f	2026-06-04 14:25:55.413178
0750ca6e-317a-490f-9f87-1041c547178a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	qwen2.5:7b	1264	39	1303	1497	t	2026-06-04 14:28:07.364997
5f436d74-4fe0-47e8-a4fa-123b74ef4644	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp_ai	qwen2.5:7b	1188	38	1226	1401	t	2026-06-04 14:29:08.331959
a3ba214d-b552-4b0d-b8e3-b623d9122ee4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp_ai	qwen2.5:7b	1188	42	1230	1614	t	2026-06-04 14:30:45.871575
59d9dc30-415e-46e3-a684-0d9f0453fed0	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	1142	18	1160	1651	t	2026-06-04 14:33:57.24603
e72b7884-c2c0-4157-9b0c-73cbf7687ef8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fin_parada	whatsapp_ai	deepseek-chat	1145	46	1191	1236	t	2026-06-04 14:34:20.600149
462de129-a9d3-48c9-b177-a5fcb9209038	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	1100	13	1113	1170	t	2026-06-04 14:34:39.077587
d66a954f-e333-413f-bd85-c0f2db8dff6b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1095	59	1154	2133	t	2026-06-04 14:58:23.689095
9e023e95-0f95-4cfd-a155-f286027d060b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1109	53	1162	1645	t	2026-06-04 14:59:00.822165
0df4c5db-1164-46ad-9adc-f001779d04ce	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	60122	f	2026-06-05 10:42:57.828143
eca1af5e-fdcf-4976-b74d-2794d3ffae43	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_fallback	qwen2.5:7b	0	0	0	11791	f	2026-06-05 16:51:21.556884
bbe91638-1d27-4ddc-9485-d75599512bec	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	11292	f	2026-06-05 16:52:45.063152
9ce36c0e-3b02-4dff-9f27-695b43ec202f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_fallback	qwen2.5:7b	0	0	0	11082	f	2026-06-05 17:11:25.185477
f3ecb045-dcf6-4d6f-8f4f-3bdbbf8d0c7d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	11032	f	2026-06-05 18:18:32.833064
9fb6734a-40c0-40a0-82c3-91e415db3636	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_fallback	qwen2.5:7b	0	0	0	60152	f	2026-06-06 08:37:04.084086
b7a34bf6-7bcc-4854-9010-eb745e304c0d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	60155	f	2026-06-06 09:23:37.626461
1b8b3508-98ea-4a1a-a909-d9a3c82dd627	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	60145	f	2026-06-06 09:39:50.891452
16fe65b2-d11b-4d4a-926d-3130dfdb6fc3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	60141	f	2026-06-06 09:50:04.376698
03297fa6-44ba-4670-a7ed-a8cd0b8f9ff2	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_fallback	qwen2.5:7b	0	0	0	60100	f	2026-06-06 14:16:31.957433
7d16c6fc-b41b-41f6-b3ba-70855a9cfe0d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_fallback	qwen2.5:7b	0	0	0	60112	f	2026-06-06 14:28:01.940219
f67cd9d9-8db3-4d47-9eaa-678736165c14	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1257	37	1294	1183	t	2026-06-06 14:55:46.73099
e6bf171b-1a41-44d1-b918-67237a4f1a9d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1186	37	1223	1543	t	2026-06-06 15:01:19.350036
a4d62237-72c4-4707-9be6-398b0d47a752	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1182	31	1213	1381	t	2026-06-06 15:01:47.094582
c1a195a3-2fda-4a81-bc59-d4529299ce89	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1233	30	1263	1411	t	2026-06-06 15:02:00.354457
4f1483db-392d-44c3-9c8b-fd5033253860	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1511	35	1546	1631	t	2026-06-06 15:05:14.999079
e885cd3f-39f8-471a-9da9-496903c02dd0	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1560	51	1611	1379	t	2026-06-06 15:08:49.639575
73504280-3142-42bb-8d10-7185a076144d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1497	28	1525	1360	t	2026-06-06 15:08:56.823727
187533d2-5bb0-4007-a27f-3149de1b118e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1518	65	1583	2401	t	2026-06-06 15:15:22.15658
2da87e3f-d41e-4650-a604-9334bf440f5a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1553	37	1590	1233	t	2026-06-06 15:15:41.530778
b89da327-e390-4337-aa78-82555c8668c6	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1538	28	1566	1366	t	2026-06-06 15:18:25.548736
c93a55f0-6957-4718-8fc5-40e680f631d8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1569	37	1606	1390	t	2026-06-06 15:18:45.092495
23278c31-f692-4e68-91f7-ed46130766cd	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	1548	28	1576	1449	t	2026-06-06 15:18:50.965949
dac6d9e5-8e1a-48f4-9f38-fe5e969e176e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1557	54	1611	1983	t	2026-06-06 15:19:15.220714
3ae37331-799d-4337-aa2a-fdfad568a925	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1520	51	1571	1515	t	2026-06-06 15:19:42.404873
6f7a2b08-826d-4b1e-8b19-2a730a7ba3a8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	confirmar_documento	whatsapp_ai	deepseek-chat	1552	47	1599	1364	t	2026-06-06 15:20:00.020162
fc10682d-058d-4922-a5d4-3d23c87c30e4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1535	26	1561	1460	t	2026-06-06 15:20:05.925888
ca87c383-78a7-46c0-a5b8-8e5a517fa70e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	1589	46	1635	1448	t	2026-06-06 15:46:36.10849
ad546d55-47c2-46f2-8b47-619d8410c6bb	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	1583	27	1610	1528	t	2026-06-06 15:46:46.192622
39c0bec7-9981-4888-b6a9-126428ceefbc	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	1666	61	1727	1857	t	2026-06-06 18:00:14.959419
d1d0b9dc-72d9-48ee-a3ac-1d68fccad302	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1661	47	1708	1579	t	2026-06-06 18:00:36.480923
8a11a5af-e18c-4544-a407-5eb373fab2b8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1653	55	1708	1473	t	2026-06-06 18:01:13.572626
7dcb6d57-7361-443d-b5d7-0011cad1fd5b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1686	65	1751	1339	t	2026-06-06 18:09:08.505915
a938f9a6-ec3f-475d-89e3-38b4aebae7c3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	1757	61	1818	1582	t	2026-06-06 18:12:41.114438
a21cabce-27e6-404c-b40a-e95f23756ec3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2040	80	2120	1684	t	2026-06-06 18:19:09.394725
c438ed41-767a-4682-975a-ddce8d6b76b3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2041	60	2101	1667	t	2026-06-06 18:25:49.576014
f7e8af83-cd94-4619-b25c-480ee41b9d0e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	1973	10	1983	1108	t	2026-06-06 18:32:23.594365
9dcfe14c-75dd-49b5-ae8d-057a0ce147ba	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	1973	10	1983	998	t	2026-06-06 18:41:51.947154
b09d9eda-f71c-413c-8036-3db462c3e8f8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_ai	deepseek-chat	2022	10	2032	1473	t	2026-06-06 18:50:08.231809
476768db-01f3-45d3-afb8-56fdc9afaccd	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_ai	deepseek-chat	2136	68	2204	1517	t	2026-06-06 18:54:19.195882
82bfc56e-6430-40de-9c35-596f75859b4b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_ai	deepseek-chat	2165	44	2209	1270	t	2026-06-06 18:54:27.801882
d088c8c6-8868-46c5-8174-5f394a930ffe	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	consultar_saldo_vacaciones	whatsapp_ai	deepseek-chat	2170	29	2199	1325	t	2026-06-06 19:31:07.896821
93f95d34-1879-4ca4-9841-21a16c63cba6	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2145	41	2186	1249	t	2026-06-06 22:20:59.03068
30085114-8976-49f2-8a5e-a2df6221a6b5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2125	28	2153	1143	t	2026-06-06 22:21:04.239564
c5f3434b-f38f-41bf-94af-79a434510c2a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_fallback	qwen2.5:7b	0	0	0	129	f	2026-06-07 07:52:52.988164
2da267eb-3613-4136-ac4a-7666e588c9ce	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_fallback	qwen2.5:7b	0	0	0	118	f	2026-06-07 07:52:57.050411
535ff7db-63e0-4dbd-bbeb-13d4c77ec12c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_fallback	qwen2.5:7b	0	0	0	117	f	2026-06-07 08:13:53.259017
f60a5566-dc30-4909-bc25-289f3838f542	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_fallback	qwen2.5:7b	0	0	0	119	f	2026-06-07 08:14:03.816744
c42e6120-e5cf-4201-9b10-2205607a10f9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp_ai	deepseek-chat	2610	69	2679	1725	t	2026-06-07 08:23:28.386585
ba111578-fcf2-491a-949e-242fd8f9e4e8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_ai	deepseek-chat	2621	96	2717	1959	t	2026-06-07 08:23:54.858134
c44ffa66-f873-4e54-8e82-a48029766fb5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_ai	deepseek-chat	2562	61	2623	1611	t	2026-06-07 08:24:02.375514
c231e514-2e3f-4c43-a309-05c4ae76a34a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2562	44	2606	1542	t	2026-06-07 08:24:11.2114
f13e8a7a-ccf9-4d15-9c72-1cbcd7a0e4d4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2529	48	2577	2011	t	2026-06-07 10:04:32.113675
73e80972-fbe3-43ea-9345-4ff72fdc4c6a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2525	40	2565	1487	t	2026-06-07 12:14:44.92196
5d70eed6-d5a0-4e3b-a49f-563e42b2dedc	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2502	28	2530	1814	t	2026-06-07 12:14:51.115513
732bcb03-0220-43d2-81ea-e8e7b8e12730	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2505	40	2545	1555	t	2026-06-07 12:15:09.840328
35ca423f-5f4d-4e92-bd73-d2b71b07595d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2506	28	2534	1596	t	2026-06-07 12:15:16.88575
af7438b1-65ea-4bc4-8d37-a4cc08943a28	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2512	28	2540	1387	t	2026-06-07 12:15:31.54401
995de3f1-1d71-410d-b459-28c999f3ee9f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2536	40	2576	1606	t	2026-06-07 16:44:09.981607
1f18d1e8-3825-43d0-8d8e-e43a8cb71c9a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2510	28	2538	1161	t	2026-06-07 16:44:14.548495
a6c3c142-557a-48e9-b089-6d0e8b97507f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2533	28	2561	1420	t	2026-06-07 16:44:42.999379
dc3f1778-3915-4aba-8184-e1b96f8595b5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2562	40	2602	1628	t	2026-06-07 17:40:42.103618
2753ef9b-5fa3-4d4f-a79a-9cd4ce4d4b2a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2536	28	2564	1648	t	2026-06-07 17:40:48.421154
466efa4d-e47c-4ea9-b5c1-951c27773d13	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2555	41	2596	1325	t	2026-06-07 17:49:34.667036
74a224b3-01c4-45dc-8a01-651aafe71875	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2542	28	2570	1520	t	2026-06-07 17:49:39.786951
2c01bc28-7430-4cbe-bcbc-91a8979bc950	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	desconocido	whatsapp_ai	deepseek-chat	2341	54	2395	1573	t	2026-06-07 21:18:14.12773
80d9d7fe-1416-4b1f-8676-7991b6fa4a01	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2377	37	2414	1419	t	2026-06-07 21:18:45.694676
30d2ec33-a1bc-4cb8-bbf5-e00495ad58ee	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2426	28	2454	1550	t	2026-06-07 21:18:50.49535
939f98c7-8fee-413d-99f6-9f3af60ac1e4	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2506	28	2534	1261	t	2026-06-07 21:19:22.19314
7e871bea-fca7-4aee-86e4-d5bd03ba0f2c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2507	38	2545	1784	t	2026-06-07 21:19:32.156552
69376d5e-6585-4b49-83f0-40318deae6ac	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2492	28	2520	1347	t	2026-06-07 21:19:37.170335
0d663335-5931-432c-9779-bcc6dbba8bd2	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2557	28	2585	1462	t	2026-06-07 21:19:59.74613
7aefba57-31f6-422b-b1ae-8dc1bcce3228	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2530	55	2585	1669	t	2026-06-08 11:18:24.515947
b47ac90f-3164-4176-84bd-d0e58d4625c5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2543	50	2593	1388	t	2026-06-08 11:18:42.894973
0da3a0f0-e2e8-472d-95ca-e7b45615766a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2540	40	2580	1508	t	2026-06-08 11:20:45.162588
7321dfd9-2665-41c4-ab30-4ebaa3a977d4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2505	28	2533	1075	t	2026-06-08 11:20:51.747432
7166f7ea-64a8-4fbd-82b2-a250f38bcad2	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2550	46	2596	1554	t	2026-06-08 11:33:26.89437
567d9a94-f1a2-40d4-b27e-4a0aba4f6a53	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2563	41	2604	1883	t	2026-06-08 11:33:37.054353
7a45d4d5-2b1d-44e6-a3f1-44b6b92b4c18	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_ai	deepseek-chat	2588	104	2692	2702	t	2026-06-08 16:41:59.067664
4a9f6972-1866-4949-8775-ac1c6978acd7	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_ai	deepseek-chat	2597	101	2698	2265	t	2026-06-08 16:42:25.399355
eadc20f2-01e7-4515-aa05-4d5a4ee5390c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_permiso	whatsapp_ai	deepseek-chat	2615	58	2673	1914	t	2026-06-08 16:42:34.359962
16052802-cad6-44e2-a035-2e30322039e1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2408	56	2464	1749	t	2026-06-11 03:58:15.926035
4e8ef84a-90a9-40e9-9f75-c5b1963e20f4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2444	37	2481	1237	t	2026-06-11 03:58:29.162148
b1620f28-6a72-4c99-8247-a38a2a79c4e4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2493	28	2521	1758	t	2026-06-11 03:58:36.728176
3d91eb12-04e4-4b11-b82d-2e8fab863f57	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2623	28	2651	1537	t	2026-06-11 07:18:20.043535
ad49cfff-7363-42ec-b2e9-6731c72fddc0	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp_ai	deepseek-chat	2635	43	2678	1512	t	2026-06-11 09:59:25.464572
8a84fdcd-dcef-4353-bfe4-74cbc5a6850a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp_ai	deepseek-chat	2589	27	2616	1412	t	2026-06-11 09:59:32.288897
68443687-b21d-4f6a-84ed-434242d2022b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2580	12	2592	1440	t	2026-06-11 11:43:47.577106
8e4cbde3-c23c-436a-9bfb-005e385cbdfb	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fin_parada	whatsapp_ai	deepseek-chat	2569	38	2607	1507	t	2026-06-11 11:43:55.954329
ea01052e-e70b-4da5-b174-545f9923d8a0	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fin_parada	whatsapp_ai	deepseek-chat	2560	26	2586	1462	t	2026-06-11 11:44:01.01929
c3c7933f-2214-4e46-8089-14f80b27acb3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2567	49	2616	1755	t	2026-06-11 14:01:34.031522
2d7319aa-b7c0-4aa8-89a1-3bd740c34195	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2505	40	2545	1476	t	2026-06-11 14:16:24.902191
01733948-fe72-418e-a243-0f4bd72bbd8f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2521	28	2549	1347	t	2026-06-11 14:16:29.668375
69ce1388-00a9-486b-9e01-5fc218b423d2	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2558	38	2596	1723	t	2026-06-11 18:53:43.44032
aec7ed02-1e06-4c81-a4eb-525f68f19889	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2552	28	2580	1960	t	2026-06-11 18:53:58.219777
a54b9ea6-ef21-4947-be4c-f1d0f148eee9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2497	40	2537	1347	t	2026-06-12 06:46:13.436328
5363a166-cc99-40e0-8012-d79d8ab8950a	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2419	39	2458	1334	t	2026-06-12 11:21:28.756849
7de228c9-058c-465e-8409-7f486688367d	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2471	28	2499	1598	t	2026-06-12 11:21:43.874872
5f962480-d975-47ba-a213-1e59b6a1fda6	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2558	69	2627	2263	t	2026-06-12 11:22:54.865008
a75a5e45-d754-48da-bed1-1840f156d1cb	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2620	100	2720	2278	t	2026-06-12 11:23:12.103086
b42a63d2-f824-43fa-a8b8-c29bad86d3fd	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2609	71	2680	2093	t	2026-06-12 11:23:25.491952
85dc436a-9f0a-4c8d-98df-1c310970e795	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	consultar_saldo_vacaciones	whatsapp_ai	deepseek-chat	2651	29	2680	1238	t	2026-06-12 11:26:31.542575
0bcea620-4fc5-491f-badf-ffafd5661978	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	solicitar_permiso	whatsapp_ai	deepseek-chat	2671	95	2766	2180	t	2026-06-12 11:26:57.084633
f2c868cc-0f14-489d-94de-d42d9c2db650	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	solicitar_permiso	whatsapp_ai	deepseek-chat	2633	70	2703	1933	t	2026-06-12 11:27:10.408239
d406714f-6f80-4673-9c9a-177e6c49460c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2520	40	2560	2026	t	2026-06-12 14:42:26.153646
c6df23b1-761c-41f3-a2be-a0d0d173a0b1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2523	44	2567	1654	t	2026-06-12 18:16:20.885493
5f3284ee-d7ca-4d7d-83d9-2cb760db0562	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2508	40	2548	1316	t	2026-06-13 15:49:08.300343
70e7cc12-4dc3-4561-a0e2-f2af0aa304bd	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2527	28	2555	1704	t	2026-06-13 15:49:12.922304
99bb71b1-b90a-4179-8f06-25e1498bbbfe	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2642	39	2681	1202	t	2026-06-15 07:29:49.169307
f3cf1e62-508f-4803-86d6-7535795bfda2	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2593	28	2621	1502	t	2026-06-15 07:30:45.30541
e3df1c3d-b414-46f6-b86a-5d5b15b4481d	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2415	39	2454	1400	t	2026-06-15 07:47:01.831077
da0039b1-f1ad-4b9a-a9c3-027e68063ed0	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2466	28	2494	1335	t	2026-06-15 07:47:13.700455
cddb8bc1-629d-4ead-ae14-8b4d4d3d489e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2552	54	2606	1569	t	2026-06-15 07:48:01.993673
d21d06ef-c7c0-4f64-87b7-a09df3a7681e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2595	34	2629	1699	t	2026-06-15 07:48:07.359711
eb69ffc1-fda8-4b4a-a666-a3ef8bf0d87b	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	desconocido	whatsapp_ai	deepseek-chat	2594	59	2653	1824	t	2026-06-15 07:48:26.201684
50421f29-b153-4bc9-8f44-4d41e5b51d39	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2586	43	2629	1398	t	2026-06-15 07:49:04.837812
2c7ae6ff-1242-4843-bea5-1afb38319cae	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2616	59	2675	1836	t	2026-06-15 08:18:49.300759
b2d953f6-0449-4dc0-977c-d98f9b0aa53c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2617	93	2710	1891	t	2026-06-15 08:18:58.570665
ffa09a93-300a-4ace-a165-ae9363bbd27d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2530	40	2570	1536	t	2026-06-15 08:24:45.310533
160f133f-2977-434f-8650-9e2e156f715c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2538	28	2566	1946	t	2026-06-15 08:24:52.097272
bf0c7184-98c6-4c80-9261-0dbe606669aa	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2609	100	2709	2643	t	2026-06-15 08:33:14.301396
e9b43d0d-a7e7-4575-95a8-d935d8b3e4b3	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2603	116	2719	2188	t	2026-06-15 08:33:22.630081
95f8adcc-3b45-4c2c-bb1c-a1cc6274f1b7	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2616	55	2671	1893	t	2026-06-15 08:36:38.470653
efabf0ff-65a9-4745-8cc5-ee1d3b7f1ec4	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2565	38	2603	1440	t	2026-06-15 12:23:10.340781
69d9d235-7a76-4ec1-a568-39d50bdb4e55	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2550	38	2588	1810	t	2026-06-15 12:35:08.049476
8ccd3fc6-66b4-4148-84b3-39255d1e3818	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2616	38	2654	1605	t	2026-06-15 14:29:50.489311
a8f5a80a-425a-4064-bef9-64dced64cb7f	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2580	46	2626	2009	t	2026-06-15 14:30:01.030902
7a3e4581-4c72-4dbb-99ef-025a245376f1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2539	56	2595	1780	t	2026-06-15 14:32:42.990985
6f4fa900-3aac-4c7b-a8ec-55aa20ad663b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2558	47	2605	1823	t	2026-06-15 14:33:02.450556
a06c889c-2df3-4477-b53c-16a75cdbf1ce	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2577	52	2629	2182	t	2026-06-15 14:34:13.839633
8f5cd50c-7fa2-466c-8fa8-ad3e976b9f7f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2549	55	2604	1682	t	2026-06-15 14:38:39.082872
6fbd2e09-fe1e-4076-941f-6e804630605f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2547	55	2602	1806	t	2026-06-15 14:55:11.778159
35c472c2-985c-47b3-ba1a-56b7f92d6723	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2547	40	2587	1644	t	2026-06-15 16:10:39.523525
0c45ddd9-ab09-4c73-8877-92c2e304f33e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2560	28	2588	1333	t	2026-06-15 16:11:36.291311
bb204f98-6795-4d52-9198-60cd9eca6589	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2568	41	2609	1271	t	2026-06-15 16:24:30.911528
8bc7cf16-3087-4ccf-8945-2df0007b259c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2544	28	2572	1122	t	2026-06-15 16:24:35.359944
3baa7e9a-77ce-47e9-b6c3-4faf3e4dfdc5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2528	49	2577	1291	t	2026-06-15 17:06:27.418224
dfad70ec-ceea-437f-baea-323ef3962c9f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2531	37	2568	1385	t	2026-06-15 17:06:40.974605
9b36359e-deb5-4205-a255-1ece5065154f	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	inicio_parada	whatsapp_ai	deepseek-chat	2531	41	2572	1258	t	2026-06-15 17:07:11.807336
c936eb17-8639-466e-a0c6-618b261990fe	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2512	58	2570	1556	t	2026-06-15 17:07:42.741315
5a02de7c-a303-4594-a63d-eee1b922c3fb	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2523	45	2568	1550	t	2026-06-15 17:07:55.466113
3a09b8c3-000c-48fb-a9e8-66d68bd6d896	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2538	37	2575	1650	t	2026-06-16 05:07:36.115652
e858f820-6e4d-41db-a1c0-3281c8883422	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2524	28	2552	1552	t	2026-06-16 05:07:42.370546
5f9b43c4-981d-493e-b27a-c52ab3710ab7	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2527	37	2564	1262	t	2026-06-16 05:30:22.897288
adc9e000-d5ba-4ba0-9d3f-ea71eec1b8c8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2534	28	2562	1156	t	2026-06-16 05:30:28.492102
f9111f93-c3cb-46ba-b59c-91581e389766	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2518	40	2558	1108	t	2026-06-16 05:43:39.067029
b9732b12-d2dc-4e7a-b1bd-3d4ef34fd82d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2510	28	2538	1531	t	2026-06-16 05:43:45.612841
ca003609-4f67-47a0-aedb-ddec219c11ba	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp_ai	deepseek-chat	2567	84	2651	1749	t	2026-06-16 05:44:24.676828
47d3235d-4822-4df3-821d-b32b2d87429d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp_ai	deepseek-chat	2571	58	2629	2355	t	2026-06-16 05:44:31.654384
1ccb5582-88c8-447b-b092-343f7825845d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2594	62	2656	1736	t	2026-06-16 07:26:41.45449
f9e8976c-57a3-4983-b0a8-a313281763f5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2577	49	2626	1487	t	2026-06-16 07:26:54.782898
2503a155-c5e3-42bf-afb1-93f2df370a6e	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2582	56	2638	1788	t	2026-06-16 07:27:10.171529
4df00786-137c-483b-b2a4-c38a91a76f9a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2556	60	2616	1791	t	2026-06-16 07:33:56.56531
eaff7084-9fa3-4f23-9145-c86342484073	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2516	37	2553	1759	t	2026-06-16 07:42:11.210438
c56fee41-9244-4c40-a6d5-b7e0e8333b86	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2564	67	2631	2003	t	2026-06-16 07:44:55.342848
16b38c34-4d8e-418c-8e3b-29d6d746b9bf	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2554	37	2591	2023	t	2026-06-16 08:01:26.299123
d47b61b7-5cc1-4702-931f-607fa0241684	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2571	41	2612	1491	t	2026-06-16 08:04:53.458025
954c7ace-c59d-4331-ae85-76f53a7ee3bb	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2569	28	2597	1386	t	2026-06-16 08:04:58.063007
d69a47de-6ec6-4a62-9193-7e956c2cdaa9	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2562	103	2665	2068	t	2026-06-16 08:05:52.0239
333d0c13-07a0-4b18-9bb5-33f2513c8d40	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	reportar_incidencia	whatsapp_ai	deepseek-chat	2580	77	2657	2340	t	2026-06-16 08:05:59.035394
d5810030-57d2-4d8f-90bf-47955d39ad1b	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2643	66	2709	1458	t	2026-06-16 08:06:23.09551
8daee7ec-9f48-48c7-9286-dbc3a1c15829	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2576	44	2620	1688	t	2026-06-16 08:06:28.511149
723eb8d6-f627-4f3c-aaa2-8d01cdea925e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2622	69	2691	1878	t	2026-06-16 08:07:08.307934
84fa25c5-b144-4118-86ef-e23dc0cbb02d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2583	92	2675	2157	t	2026-06-16 08:12:10.291435
0b06ed11-7f99-4190-8f8e-76004d396887	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp_ai	deepseek-chat	2591	77	2668	1970	t	2026-06-16 08:13:22.942402
c0727786-fae4-4377-82d9-22c90786be43	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	solicitar_vacaciones	whatsapp_ai	deepseek-chat	2553	58	2611	2021	t	2026-06-16 08:13:42.085547
f48e8c12-4c62-49fc-aedb-2872fdf94cd8	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2592	38	2630	1756	t	2026-06-16 12:19:53.824032
90daf0b2-0ff1-44f3-a675-5779f70c7b73	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2578	43	2621	1737	t	2026-06-16 12:20:08.373054
6cf359aa-620b-4922-9e4d-95d2897753b5	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2554	37	2591	1558	t	2026-06-16 12:20:13.265625
79072a57-21a6-454d-aa25-da8a087cf676	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2551	38	2589	1668	t	2026-06-16 12:43:54.919761
afa6c82b-c033-49b6-9e3c-8eccad859bc5	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2571	28	2599	1762	t	2026-06-16 12:44:01.357457
ff3088c3-a5a8-4a5a-bae6-cb8c45102607	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2573	38	2611	1455	t	2026-06-16 13:38:50.397988
a65109fb-b951-455b-a10f-87120ae88c29	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2562	49	2611	1674	t	2026-06-16 14:41:04.302582
8d320aa7-7c55-4c7c-a66d-d66bd59caab4	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2586	50	2636	1572	t	2026-06-16 14:41:15.463851
af31cd4a-1c6d-4381-ad1a-b0933aa22461	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2578	48	2626	1560	t	2026-06-16 14:41:28.700298
e2537f40-30cf-4f8e-8ac0-d0e29628dbc3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2575	52	2627	1898	t	2026-06-16 14:50:02.489417
2d3ba1e8-e9cb-41c8-ab26-3daacee932ce	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2558	41	2599	1657	t	2026-06-16 16:15:11.089933
b8834fb1-c7b3-423f-bb6d-be2f8b130d0c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2546	28	2574	1471	t	2026-06-16 16:15:22.16279
0173a66b-4fdf-4a95-8c9a-9164b70d7a1b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2537	39	2576	1213	t	2026-06-17 05:41:46.398418
8534a9a6-4fae-40e8-96ad-4a652610cded	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2545	37	2582	1283	t	2026-06-17 07:28:03.174437
9f9adb4a-73ca-4e2b-8fdb-d4b5360d408e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2544	37	2581	1727	t	2026-06-17 07:28:10.001813
b982a2e7-fc84-40c6-ba2a-88ab2dca528b	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2529	37	2566	1259	t	2026-06-17 09:43:52.584444
633e7300-e99a-4da3-a89e-e57d581109cb	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2426	40	2466	1391	t	2026-06-17 09:52:00.891391
b5605269-2c61-48e4-9438-844f1410a76e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2478	28	2506	1340	t	2026-06-17 09:52:10.433858
8bce3c6d-0597-43c4-a0b0-010e49ffdaec	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2561	60	2621	2457	t	2026-06-17 09:52:47.737518
3a8aee9c-3222-4bc8-a263-659f25456117	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2599	94	2693	2137	t	2026-06-17 09:53:07.526015
efe5d80a-8fdf-466a-ac1c-0c60515ffae4	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2609	87	2696	2310	t	2026-06-17 09:53:13.196143
22a864a6-aa04-427c-832b-5a85c53c616c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	reportar_incidencia	whatsapp_ai	deepseek-chat	2588	73	2661	1987	t	2026-06-17 09:53:16.735974
2dc3d74f-a7fd-4ff5-829d-4c6374090b6c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	confirmar_documento	whatsapp_ai	deepseek-chat	2594	27	2621	1449	t	2026-06-17 09:53:27.833176
33f7f6b0-aba7-4f4f-8f17-1a5c8a8fa1f9	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2531	42	2573	1300	t	2026-06-17 09:53:45.720541
e15be286-5821-43d6-98d4-264d0ee46309	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2524	34	2558	1714	t	2026-06-17 09:53:51.723066
f1e47c0c-69be-493b-b488-8f8464180eb6	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2568	34	2602	1722	t	2026-06-17 09:55:09.559004
4060fd2e-1394-43f6-98ad-850a0431e93c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2583	38	2621	1355	t	2026-06-17 12:21:47.75149
04dcadfc-477d-4525-8551-a6669496856c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2576	28	2604	1774	t	2026-06-17 12:22:00.265152
064e4324-079c-4124-9194-33ab826d615d	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2577	41	2618	1343	t	2026-06-17 15:51:30.386278
dba98d55-5f6f-4391-8b2d-029d7a03fc72	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2557	28	2585	1396	t	2026-06-17 15:51:36.051578
259c47c0-5d75-4553-8802-8a8631c19a32	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2556	44	2600	1949	t	2026-06-17 16:22:03.146496
dc88ba7b-87bf-4d89-9536-ae9a92ca4de9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2544	28	2572	1632	t	2026-06-17 16:22:08.336281
a8ec706e-6eb7-47bb-a652-c6ca575da538	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2554	54	2608	1442	t	2026-06-17 16:22:44.657064
a05261ea-b8d8-4681-9207-256d9adbe704	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2545	47	2592	1601	t	2026-06-17 16:22:53.680065
39f16416-25e0-4965-862d-52383530be68	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2541	28	2569	1767	t	2026-06-17 16:22:59.411573
4240fdc1-6baa-4b26-924d-3e416e18705a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2547	28	2575	1242	t	2026-06-17 16:23:16.794363
854bd5d4-194a-4b18-ae97-86ead9fa4544	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2555	73	2628	1681	t	2026-06-17 16:23:39.591742
94549a45-5aab-4be9-ad8c-93f517856d6b	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2582	42	2624	1456	t	2026-06-17 16:23:55.079694
1a6b9d6f-f7f4-42a1-bd28-262ca7dd4408	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2550	39	2589	1490	t	2026-06-18 05:17:08.23455
0dfaaeec-21fc-40ae-a8d4-edb0f88b3f05	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2560	40	2600	1209	t	2026-06-18 05:17:24.706524
ce5d9611-c9e0-4bd5-a852-ca9a5ed17df1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2565	28	2593	1597	t	2026-06-18 05:17:31.964345
31527a41-7d99-4744-a908-6528f8c8fa4a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2573	43	2616	1239	t	2026-06-18 05:18:39.229803
cbcbff27-3fce-4d90-bea5-832f033d4ae5	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2556	39	2595	1368	t	2026-06-18 05:18:52.607659
40345ebc-e1c4-40e8-94f2-36241c871aaa	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2576	58	2634	1340	t	2026-06-18 05:19:12.650143
d120294b-9080-4a49-b804-007b55b682c1	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2581	28	2609	1581	t	2026-06-18 05:19:27.919114
5cadd7a9-cddf-4de9-b50d-7c608adb531c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2589	28	2617	1050	t	2026-06-18 05:19:54.19591
85bcb489-3d94-4b03-b910-5e47afb91bac	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2597	67	2664	1363	t	2026-06-18 05:20:24.367875
ec0b3f1d-621d-49ea-9327-efb3c9dad747	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2572	67	2639	1630	t	2026-06-18 05:21:44.457084
dae8cddb-8674-442b-84b6-9a7796b342f9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2662	55	2717	1498	t	2026-06-18 06:15:41.733143
feb1de2b-f9fa-4d39-9201-17b3f9ee9845	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2529	40	2569	1303	t	2026-06-18 06:59:53.260653
aa30c4db-2a21-448d-a819-935350a8aab0	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2545	28	2573	1731	t	2026-06-18 07:32:12.596274
0032071d-2b03-4d6e-97ec-f9e3ef52d5d0	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2576	67	2643	1528	t	2026-06-19 06:04:13.501631
73af84ca-adbd-48d0-b7a7-135637c973bf	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2567	38	2605	1391	t	2026-06-19 06:27:27.03307
fe4673eb-95cc-4b03-b407-899953f5b4ef	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2602	40	2642	1162	t	2026-06-19 07:38:57.119024
6fb8b5ec-b7cb-450a-8666-c09edfc00105	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2580	28	2608	1268	t	2026-06-19 07:40:09.414676
0fb2b6ba-85c2-4406-b041-eb81f4f73013	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2563	40	2603	1362	t	2026-06-19 07:40:15.316946
ac82e9a7-e9ad-4d15-adc9-9ec670d6bf6b	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2562	28	2590	1313	t	2026-06-19 07:40:19.271252
5dd917c0-3adf-4bda-8704-dbd35ea7c125	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2488	28	2516	1748	t	2026-06-18 06:59:58.560687
5838b1d8-6076-4dd5-9b94-397b7895b9ac	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2426	40	2466	1464	t	2026-06-18 07:05:16.739774
d96d51fd-5be0-430b-b8d1-2028b1a3f277	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2553	37	2590	1343	t	2026-06-18 07:32:06.921393
a6de9120-2d0f-4873-8b98-7248b17f3c74	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2554	28	2582	1711	t	2026-06-18 07:35:21.877411
20df270c-06a3-4cb6-b1ec-74082d438ecc	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2634	43	2677	1426	t	2026-06-18 07:53:19.235765
66e4f276-a070-45cd-aafd-2747da6c1272	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2478	28	2506	1901	t	2026-06-18 07:05:24.548864
da39ee6e-e4c1-49d6-859a-b40e3e9907bc	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2533	40	2573	1732	t	2026-06-18 07:35:16.719524
11399efe-1a04-4b93-bb3d-060cfa20eaff	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2621	69	2690	2111	t	2026-06-18 07:53:31.538947
d04f86d8-8c8a-4731-a113-23fbab43c7c3	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2573	72	2645	1919	t	2026-06-18 07:56:57.395881
624fda79-c52f-4c53-b543-01dbd8a53543	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2560	28	2588	1595	t	2026-06-19 06:03:21.848866
24aff11e-b829-48ff-a29b-dde0aa75e12a	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2568	28	2596	1341	t	2026-06-19 06:03:48.985074
825eb310-7daf-40e2-9100-5690c66e5344	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2596	63	2659	1542	t	2026-06-19 06:27:13.424575
b5b63c64-4f7d-4df1-8a20-97bfc9c4beee	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2539	28	2567	1303	t	2026-06-19 06:28:51.925601
81963112-10f5-4674-8fdc-1f56cb157d74	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	solicitar_vacaciones	whatsapp_ai	deepseek-chat	2607	81	2688	2378	t	2026-06-19 07:22:57.975491
e787ae38-b4e6-4022-8af4-5febf6eef819	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2532	37	2569	1404	t	2026-06-19 07:32:27.135829
156f73f3-6d04-46bd-af94-88efbe2ddbd1	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2606	57	2663	2411	t	2026-06-18 10:15:37.641628
a04410d0-73e3-448d-8568-2b37a4495ada	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2514	37	2551	1434	t	2026-06-19 06:29:37.783729
2c3a762f-6651-4d3f-8ee4-af568b9a2bfa	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	solicitar_vacaciones	whatsapp_ai	deepseek-chat	2586	58	2644	1808	t	2026-06-19 07:23:04.394605
95eed213-ac32-4dd5-9c74-231eb893613a	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2595	41	2636	1503	t	2026-06-19 07:40:05.065888
cf5f335d-9d2d-405f-a0ea-6ca8a8407a0f	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2600	38	2638	1786	t	2026-06-19 12:03:31.051292
2411b9f7-81b6-479b-90f6-4d87f17dd5bb	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2592	28	2620	1433	t	2026-06-19 15:51:15.865953
2c5c5579-3fd7-4879-ac4e-8d94e643f284	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2577	38	2615	1763	t	2026-06-18 12:08:15.19875
c5cdbd11-b105-4410-8e99-77ae239eec3d	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2571	28	2599	1599	t	2026-06-18 12:08:20.453765
17de3080-42d8-497b-8efd-815400121a24	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2593	41	2634	2017	t	2026-06-18 15:45:37.334135
a2f36e13-dab5-4e67-8fa2-09a046e54e5f	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2586	28	2614	2130	t	2026-06-18 15:45:49.346297
b15e75e9-8397-4f38-be0a-8d58a9ef5474	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2494	40	2534	1900	t	2026-06-18 17:38:57.687006
8c9ac01c-13cf-44b5-bb19-8b68c51acf81	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	desconocido	whatsapp_ai	deepseek-chat	2499	43	2542	1531	t	2026-06-18 20:16:26.698962
bb5a9fc3-c2cf-4e1b-9cf8-3ca5f96546b8	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2608	53	2661	1730	t	2026-06-19 06:02:52.745424
dc7d28d9-8472-48cc-84d6-9b03d1ff5c9d	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2615	38	2653	1413	t	2026-06-19 06:03:15.141991
30eca3fe-a43e-4c0d-ae48-df61e46d4690	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2604	67	2671	1691	t	2026-06-19 06:27:04.215582
015d83da-a3dc-45d3-86f8-4a0d749c3a5c	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2540	38	2578	1430	t	2026-06-19 06:28:47.665542
51131529-394d-4dfc-9392-47d3971323f6	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2487	40	2527	1986	t	2026-06-19 07:05:40.808522
59f99187-8644-408a-96a7-69db8d66f6a0	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_entrada	whatsapp_ai	deepseek-chat	2521	28	2549	1855	t	2026-06-19 07:05:46.836573
7ad14f3a-81c9-47ff-bc17-9f38ed48636a	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	solicitar_vacaciones	whatsapp_ai	deepseek-chat	2588	56	2644	1592	t	2026-06-19 07:22:43.199331
ad50c551-0d5a-45db-9b04-be9d4217e163	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	desconocido	whatsapp_ai	deepseek-chat	2589	43	2632	1617	t	2026-06-19 07:23:15.286625
ecb85bf6-3b32-4028-b430-a579dc8afd7f	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_entrada	whatsapp_ai	deepseek-chat	2552	28	2580	1661	t	2026-06-19 07:32:31.668346
a6ebbf36-816d-4f55-b31d-9086730f340e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	tenant_admin	fichar_salida	whatsapp_ai	deepseek-chat	2585	28	2613	1963	t	2026-06-19 12:03:35.951844
41ac81c7-6f10-48cb-9db8-2f9ba0fa60c9	951a449d-5f92-49c5-aec3-b3de06c44bcf	employee	fichar_salida	whatsapp_ai	deepseek-chat	2552	53	2605	1700	t	2026-06-19 13:10:43.257733
aca361b2-686b-4963-842c-da7cd9205a9e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2610	13	2623	1299	t	2026-06-19 15:51:10.317561
d172742d-2b52-4946-970c-872f79145211	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2602	41	2643	1837	t	2026-06-19 19:56:16.654006
a1273680-482e-4a3f-8106-da43d63a7a73	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	employee	fichar_salida	whatsapp_ai	deepseek-chat	2595	28	2623	1523	t	2026-06-19 19:56:22.490971
\.


--
-- Data for Name: ai_whatsapp_messages; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.ai_whatsapp_messages (id, tenant_id, employee_id, role, content, intent_code, created_at) FROM stdin;
364bc0b8-0155-4bdd-9582-9e95528616b9	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	assistant	✅ *Fichaje ENTRADA*\n🕐 Hora: 09:40:19\n\n📍 Puedes compartir tu *ubicación* al fichar (clip → Ubicación) si lo deseas.	fichar_entrada	2026-06-19 07:40:19.281282
da1db7a8-e020-4006-af8c-107a5ca6abf7	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	user	Salida	\N	2026-06-19 12:03:31.05285
467c42fd-e091-42ea-8a9f-833439ed8d08	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	assistant	¿Quieres fichar la salida ahora?	pending_confirmation	2026-06-19 12:03:31.065778
dce3bc5e-6deb-4cc7-be30-774db456137c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	user	Si	\N	2026-06-19 12:03:33.985186
75d8ba7e-533e-462f-804a-c5a47d8a7857	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	assistant	✅ *Fichaje SALIDA*\n🕐 Hora: 14:03:35\n\n📍 Puedes compartir tu *ubicación* al fichar (clip → Ubicación) si lo deseas.	fichar_salida	2026-06-19 12:03:35.966285
b5a2d0fd-848e-4dbe-9908-466a10e794bc	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	user	Hola jenny aún no he terminado	\N	2026-06-19 13:10:43.260984
a8cd6616-48b3-45e7-a31d-3f0904afdd0b	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	assistant	¿Quieres fichar la salida ahora?	pending_confirmation	2026-06-19 13:10:43.271843
8f597001-39c0-4432-a88e-605e62b95c95	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	user	Salida	\N	2026-06-19 15:51:10.319898
170faac8-8124-4d32-a227-50c6e6b1f9f1	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	assistant	¿Quieres fichar la salida ahora?	pending_confirmation	2026-06-19 15:51:10.330376
fd75c85f-52d0-413a-870c-4e085325b30c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	user	Si	\N	2026-06-19 15:51:14.429577
7ebbbfb8-d33a-4a99-abfe-39c24b433177	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	user	Salgo	\N	2026-06-18 17:38:57.688665
85b1c39e-fa85-40dc-94de-219e3b3ef60e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	assistant	✅ *Fichaje SALIDA*\n🕐 Hora: 17:51:15\n\n📍 Puedes compartir tu *ubicación* al fichar (clip → Ubicación) si lo deseas.	fichar_salida	2026-06-19 15:51:15.876159
b0b29dc4-f14b-44c0-bb3c-1daa6c33e3f7	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	assistant	No tienes ninguna jornada abierta. Si quieres fichar la *entrada*, dímelo.	guard_not_open	2026-06-18 17:38:57.696267
44b7dac4-bd7e-47bc-85f4-92be98321abc	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	user	Fe	\N	2026-06-18 20:16:26.700564
eb37cb68-6868-4bc8-9f62-bc93e83e55b5	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	assistant	No te he entendido bien, Benito. ¿Puedes repetirlo?	ask	2026-06-18 20:16:26.70356
c75b471b-8aad-4051-a1c8-a675481a3ef3	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	2e344a27-169d-44fa-8151-0e643749dc33	user	Salida	\N	2026-06-19 19:56:16.655538
8a932a15-66e3-4ed3-9aa1-80a6cabce376	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	2e344a27-169d-44fa-8151-0e643749dc33	assistant	¿Quieres fichar la salida ahora, Jairo?	pending_confirmation	2026-06-19 19:56:16.665119
49ecf517-00c4-42e7-a2ab-542e09c50748	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	2e344a27-169d-44fa-8151-0e643749dc33	user	Si	\N	2026-06-19 19:56:20.965226
71cbe8f7-ed00-4950-84c9-fc1e1d9900f7	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	2e344a27-169d-44fa-8151-0e643749dc33	assistant	✅ *Fichaje SALIDA*\n🕐 Hora: 21:56:22\n\n📍 Puedes compartir tu *ubicación* al fichar (clip → Ubicación) si lo deseas.	fichar_salida	2026-06-19 19:56:22.504269
27fa4204-8cda-4154-ac97-a2474593b93e	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	assistant	📍 *Necesito tu ubicación para fichar.*\n\nPulsa el 📎 (adjuntar) → *Ubicación* → *Enviar tu ubicación actual*.	await_location	2026-06-19 06:28:51.938394
0d7518f3-21f6-4d96-b91f-de4480a2c62a	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	user	Entrada	\N	2026-06-19 06:29:37.785104
c8868f3b-4aea-4892-b6af-3941a80ea387	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	assistant	¿Quieres fichar la entrada ahora?	pending_confirmation	2026-06-19 06:29:37.7937
ce4e3a7e-cd4a-4f6d-93de-a043cb3e65f8	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	2e344a27-169d-44fa-8151-0e643749dc33	assistant	✅ *Fichaje ENTRADA*\n🕐 Hora: 09:05:46\n\n📍 Puedes compartir tu *ubicación* al fichar (clip → Ubicación) si lo deseas.	fichar_entrada	2026-06-19 07:05:46.851855
64a79bc0-dabc-4fd6-86ce-ff19ef9ca4d5	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	assistant	📍 *Necesito tu ubicación para fichar.*\n\nPulsa el 📎 (adjuntar) → *Ubicación* → *Enviar tu ubicación actual*.	await_location	2026-06-18 06:59:58.571749
c58e73e8-e6ba-4ee5-9492-6e61c526f1b6	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	941a5698-80fc-41ec-87c7-1fe4fa28ba75	assistant	¿Quieres fichar la salida ahora?	pending_confirmation	2026-06-07 21:19:32.167162
08cc5af1-1e5e-4a3e-be40-514d4defd33f	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	941a5698-80fc-41ec-87c7-1fe4fa28ba75	user	Si	\N	2026-06-07 21:19:35.818138
3afce74d-1674-4008-a2a4-4842a48dcc17	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	941a5698-80fc-41ec-87c7-1fe4fa28ba75	assistant	📝 *Resumen de jornada*\n\nAntes de registrar tu salida, comparte brevemente cómo ha ido el día:\n\n• Lo que has realizado\n• Notas o tareas para mañana\n• Cualquier anomalía o incidencia\n\n_Si prefieres no añadir nada escribe *sin resumen*._\n\n📍 Puedes compartir tu *ubicación* al fichar (clip → Ubicación) si lo deseas.	fichar_salida	2026-06-07 21:19:37.178774
891e6747-8094-4265-aad8-4e78e2d33cf4	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	941a5698-80fc-41ec-87c7-1fe4fa28ba75	user	Sin resumen	\N	2026-06-07 21:19:59.747942
60b6a670-9612-418e-acbc-c336acf2a17f	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	941a5698-80fc-41ec-87c7-1fe4fa28ba75	assistant	📝 *Resumen de jornada*\n\nAntes de registrar tu salida, comparte brevemente cómo ha ido el día:\n\n• Lo que has realizado\n• Notas o tareas para mañana\n• Cualquier anomalía o incidencia\n\n_Si prefieres no añadir nada escribe *sin resumen*._\n\n📍 Puedes compartir tu *ubicación* al fichar (clip → Ubicación) si lo deseas.	fichar_salida	2026-06-07 21:19:59.757176
43fe80db-a4ee-452c-99fd-f6267e294a6a	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	assistant	Carmen, ¿confirmas que quieres solicitar vacaciones para el 19/06/2026?	pending_confirmation	2026-06-19 07:22:57.984737
0eb35cf0-6f59-46a6-8a5b-939660b4d892	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	user	Si	\N	2026-06-19 07:23:02.582706
8ea4d69a-9b0d-45a8-920c-62a2a6e1f546	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	assistant	Solicitud registrada [Vacaciones] (2026-06-19 → 2026-06-19, 1.0 días). Pendiente de aprobación de tu supervisor.	solicitar_vacaciones	2026-06-19 07:23:05.378505
0cc2b86e-1b45-4a1c-adb6-5fc3b1846bee	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	user	Ok	\N	2026-06-19 07:23:15.288056
78842718-7af2-4c2f-b27e-ad5579c61b94	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	assistant	¡Perfecto, Carmen! Si necesitas algo más, aquí estoy 😊	ask	2026-06-19 07:23:15.290748
ea688dc2-92f0-406a-b076-31203c66de42	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	assistant	✅ *Fichaje ENTRADA*\n🕐 Hora: 09:32:31\n\n📍 Puedes compartir tu *ubicación* al fichar (clip → Ubicación) si lo deseas.	fichar_entrada	2026-06-19 07:32:31.680539
\.


--
-- Data for Name: api_keys; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.api_keys (id, tenant_id, name, key_prefix, key_hash, is_active, created_at, last_used_at, created_by_id) FROM stdin;
a3d89f27-3e5f-4d3b-9966-8bd73e568b8a	951a449d-5f92-49c5-aec3-b3de06c44bcf	integracion Dolibarr	ak_uQe-LVqX...	dba8aaeb056d701c4102fe6e5bfe0b9906363787c7f310d1b65d927891465a78	t	2026-06-09 08:45:28.275228	\N	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40
\.


--
-- Data for Name: billing_methods; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.billing_methods (id, tenant_id, company_id, label, method_type, is_default, holder_name, iban_masked, card_brand, card_last4, notes, created_at) FROM stdin;
\.


--
-- Data for Name: clock_ins; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.clock_ins (id, employee_id, latitude, longitude, source, notes, whatsapp_message_id, project_id, entrada_at, salida_at, work_summary, address, latitude_out, longitude_out, address_out) FROM stdin;
bd686ef3-0e6b-4e43-b725-3806cfae2ffd	c3136edf-351e-4329-8050-720ecd216410	\N	\N	panel	\N	\N	\N	2026-06-15 07:29:00+00	2026-06-15 07:29:00+00	\N	\N	\N	\N	\N
c874e601-b7f3-4ee2-85f5-e34cd6fb974f	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.392836	-5.9831657	whatsapp	\N	ACD10B00E1B84F878166623ED9D60391	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-12 06:46:26.307846+00	2026-06-15 16:25:06.657295+00	He hecho de todo	Calle Arroyo, Sevilla	37.3930362	-5.9824317	Calle Gonzalo Bilbao, Sevilla
b99e28dd-3921-48fc-a2cb-de5d6489f7bb	f41acab0-d7a1-4441-942b-69664ceb9d3b	\N	\N	whatsapp	\N	3EB01DAF225272AF52B981	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-06 15:01:54.224753+00	2026-06-06 15:08:56.83223+00	\N	\N	\N	\N	\N
ed1a582d-0835-4ea6-a22e-f616e2a75463	f41acab0-d7a1-4441-942b-69664ceb9d3b	\N	\N	whatsapp	\N	AC3520C29FFA80EE5CAB2973FE9FEC80	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-06 15:18:29.510711+00	2026-06-06 22:21:04.246423+00	\N	\N	\N	\N	\N
a7b04d05-f9a4-4e10-b72e-9c22b84a7552	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.3931084	-5.9831061	whatsapp	\N	ACA381D7C948F766944B577D173F51D5	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-07 17:41:11.592316+00	2026-06-07 17:50:05.758652+00	Alicatar un baño	\N	37.3930923	-5.9832188	Calle Gonzalo Bilbao, Sevilla
8524cb68-0d97-4ad0-9115-583850064e2f	941a5698-80fc-41ec-87c7-1fe4fa28ba75	\N	\N	whatsapp	\N	ACA359BC683C9B2DDC2637124E183FDA	\N	2026-06-07 21:18:50.502796+00	2026-06-07 21:20:14.554929+00	Nada que aportar hoy	\N	\N	\N	\N
de30f012-8210-4dda-8a0d-db9893cbf910	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.3973693	-5.9771578	whatsapp	Se ha confundido	AC33640CC8A922C5AB77C279EF674892	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-08 09:21:00+00	2026-06-08 14:00:00+00	\N	Calle Arroyo, Sevilla	\N	\N	\N
1546eb4d-2fe9-4d74-ad9a-e2c662453fac	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.4090542	-5.9725763	whatsapp	Se ha confundido	AC0251151D1A5AA1782FD172D59D8E3B	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-07 04:09:00+00	2026-06-07 13:50:00+00	\N	\N	37.4096898	-5.9715611	Calle Pilistra, Sevilla
3b53a451-cbfb-4e35-a637-2b151961e2d7	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.3928685	-5.9829855	whatsapp	\N	ACF2AECFAEFB8A3186D5B3100E3EBB54	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-11 07:19:30.303338+00	2026-06-11 14:17:06.02408+00	De todo	Calle Gonzalo Bilbao, Sevilla	37.4096969	-5.9718462	Calle Jara, Sevilla
955d296c-f4c8-4c94-84a9-ec5876826860	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	37.413475036621094	-5.975333213806152	whatsapp	\N	3A366FA74587972DF2EC	054c928c-0a9e-4014-9daa-c012d6113c5f	2026-06-11 06:25:44.516455+00	2026-06-11 19:07:07.54265+00	Hoy he estado realizando varias tareas	Camino de Cantalobos, Sevilla	37.37678909301758	-6.002829074859619	Calle Virgen del Monte, Sevilla
49ec0b10-701c-4096-bc97-8d007980d917	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.3931406	-5.9831421	whatsapp	\N	ACBF7F45B2E9A8E1F49DBD6A9A724C41	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-11 21:17:37.220276+00	2026-06-11 21:18:24.448631+00	Lo he hecho fenomenal	Calle Arroyo, Sevilla	37.3930668	-5.98311	Calle Arroyo, Sevilla
b8e291fd-876f-4eeb-b4bb-75f0a8e9e48b	c3136edf-351e-4329-8050-720ecd216410	37.3973642	-5.9771752	whatsapp	\N	A51FB8B0D73D5D0569B3540DDE1A2AA8	\N	2026-06-12 07:30:00+00	2026-06-12 12:02:00+00	\N	Calle Arroyo, Sevilla	\N	\N	\N
8d17021b-1d9e-45a7-b8a7-fdf4093f4b27	c3136edf-351e-4329-8050-720ecd216410	\N	\N	panel	\N	\N	\N	2026-06-15 07:29:00+00	2026-06-15 12:00:00+00	\N	\N	\N	\N	\N
65261f9f-1f90-45e4-9a85-4ec4d11634b7	c3136edf-351e-4329-8050-720ecd216410	37.3973708	-5.9771727	whatsapp	\N	A58B28875FD42BA81EC3A023BC160904	\N	2026-06-18 07:32:42.217068+00	2026-06-18 12:08:20.46466+00	\N	Calle Arroyo, Sevilla	\N	\N	\N
3ce06fa4-eea3-41d9-b39f-fa528afebfd2	2e344a27-169d-44fa-8151-0e643749dc33	\N	\N	whatsapp	\N	2A90FC2FE10A274F0214	\N	2026-06-19 07:05:46.846159+00	2026-06-19 19:56:22.49956+00	\N	\N	\N	\N	\N
54b8e26b-7c48-4a10-84e3-547dbc550334	e5e24f2f-86ec-4321-8853-e394a494630e	37.397098541259766	-5.97728967666626	whatsapp	\N	3A1B69926D6713571948	\N	2026-06-16 08:06:37.473553+00	2026-06-16 12:20:22.805471+00	\N	Calle Arroyo, Sevilla	37.398014068603516	-5.975265026092529	Calle Arroyo, Sevilla
aec60e3c-e25a-4177-93ba-48bf592ec9f1	c3136edf-351e-4329-8050-720ecd216410	37.3973648	-5.9771609	whatsapp	\N	A58708DDC30848D7DAB77118BEEDF2D8	\N	2026-06-16 07:28:00+00	2026-06-16 12:44:17.307139+00	\N	Calle Arroyo, Sevilla	37.3745898	-5.9455161	Barriada Federico García Lorca, Sevilla
86c95121-b2dd-44b0-9dbe-df51e3aadd16	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.3930717	-5.9830954	whatsapp	\N	AC0203FDB4D56A0BBCB0A292D25EC486	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-16 05:44:02.867522+00	2026-06-16 16:15:43.864882+00	De todo	Calle Arroyo, Sevilla	37.4096358	-5.9717078	Calle Mimosa, Sevilla
de3886cc-42db-4235-be31-e5049b376dce	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	37.42696762084961	-5.9781012535095215	whatsapp	\N	3A12DDCDFD82DCE39102	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-16 05:31:04.414456+00	2026-06-17 05:41:34.838182+00	Entrada	Calle Tecnología, Sevilla	37.42701721191406	-5.97797155380249	Calle Tecnología, Sevilla
060a3f6b-7345-4b67-bb78-ca1248843980	e5e24f2f-86ec-4321-8853-e394a494630e	37.397300720214844	-5.977292537689209	whatsapp	\N	3AA7146D064959C82096	\N	2026-06-15 07:30:00+00	2026-06-15 12:05:00+00	\N	Calle Pinzones, Sevilla	37.397098541259766	-5.97728967666626	Calle Arroyo, Sevilla
afc11052-e6f4-44ba-bcd1-e9db162119dc	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.3930843	-5.9830969	whatsapp	\N	ACD33170284DBED7188633E7C811B6D3	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-19 06:06:42.698181+00	\N	\N	Calle Arroyo, Sevilla	\N	\N	\N
96d5b0f2-08a0-406e-af3c-0d59e9d8b3dd	e5e24f2f-86ec-4321-8853-e394a494630e	37.39728927612305	-5.977287292480469	whatsapp	\N	3A0B06330FF679F33340	\N	2026-06-17 09:54:53.781087+00	\N	\N	Calle Pinzones, Sevilla	\N	\N	\N
25979966-37b6-4e33-9080-00c2b54dc464	c3136edf-351e-4329-8050-720ecd216410	37.3973636	-5.9771517	whatsapp	\N	A5786443B986601DE4F2F655D731EC10	\N	2026-06-17 07:28:22.440806+00	2026-06-17 12:22:36.379324+00	\N	Calle Arroyo, Sevilla	37.374392	-5.9457763	Barriada Federico García Lorca, Sevilla
191f0da0-1e83-44b2-b9c8-ea5eabd701f8	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	37.397151947021484	-5.977293014526367	whatsapp	\N	3A700FB9066ECA97CF8D	\N	2026-06-17 07:30:00+00	2026-06-17 15:51:51.754407+00	\N	Calle Arroyo, Sevilla	37.38821029663086	-5.922895431518555	Calle el Campo de la Verdad, Sevilla
e0426188-9f11-4f4e-895a-d7ac586e452c	f41acab0-d7a1-4441-942b-69664ceb9d3b	37.3929659	-5.982972	whatsapp	\N	AC126965F3CFAF0E37EFD042DCCB7FC4	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-17 07:12:52.608616+00	2026-06-17 17:42:46.456784+00	Casi de todo	Calle Arroyo, Sevilla	37.3930704	-5.9830936	Calle Arroyo, Sevilla
7b22109b-0f2f-4e0e-890a-ebc38af34cb9	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	37.42706298828125	-5.978090286254883	whatsapp	\N	3A885113783C8CD4D522	a145d4f4-3f15-4c23-93bc-51a09947a031	2026-06-17 05:42:02.465373+00	2026-06-18 05:21:02.846827+00	Hoy he realizado trabajo de reparto	Calle Tecnología, Sevilla	37.42414855957031	-5.978192329406738	Calle Tecnología, Sevilla
e0120da2-c958-4210-98b7-ffbd9b97a47f	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	37.42699432373047	-5.978275775909424	whatsapp	\N	3A270E32B9EAEB6C7C7C	054c928c-0a9e-4014-9daa-c012d6113c5f	2026-06-18 05:22:00.457029+00	2026-06-19 06:29:25.636862+00	He dado vueltas	Calle Tecnología, Sevilla	37.39933776855469	-5.989396095275879	Calle Arrayán, Sevilla
6b0e7af2-44a1-4a54-aa88-4e8cd3e215ac	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	37.39931106567383	-5.9894938468933105	whatsapp	\N	3AF12833E2CC99100392	054c928c-0a9e-4014-9daa-c012d6113c5f	2026-06-19 06:29:48.747696+00	\N	\N	Calle Virgen del Carmen Dolorosa, Sevilla	\N	\N	\N
71c96dbe-2c68-4516-9484-a0cc9ed4c0a3	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	37.39727783203125	-5.977315425872803	whatsapp	\N	3ACA34A78B22EB8F8798	\N	2026-06-18 07:30:00+00	2026-06-18 15:30:00+00	\N	Calle Pinzones, Sevilla	\N	\N	\N
a6b8bde4-b5de-4e1a-9f92-66ac034274cc	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	37.387428283691406	-5.922135353088379	whatsapp	\N	3A1F1D506A52F516A2F3	\N	2026-06-18 15:31:00+00	2026-06-18 15:32:00+00	\N	Calle Zapillo, Sevilla	\N	\N	\N
0a3ba4ce-5bef-4f9b-a8e1-819eb6348dd9	c3136edf-351e-4329-8050-720ecd216410	\N	\N	whatsapp	\N	A51C32193A2D55D5E06969341063D90B	\N	2026-06-19 07:32:31.67643+00	2026-06-19 12:03:35.962295+00	\N	\N	\N	\N	\N
251a3d31-060e-4480-a05d-d50ab9327c72	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	\N	\N	whatsapp	\N	3AAA5FAE73E26C527447	\N	2026-06-19 07:40:19.27892+00	2026-06-19 15:51:15.874977+00	\N	\N	\N	\N	\N
\.


--
-- Data for Name: clock_pending_fichajes; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.clock_pending_fichajes (employee_id, record_type, latitude, longitude, whatsapp_message_id, created_at, pending_confirmation, pending_intent, pending_meta) FROM stdin;
\.


--
-- Data for Name: clock_settings; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.clock_settings (tenant_id, require_geolocation, clock_reminder_minutes, incident_reminder_enabled, incident_reminder_minutes, inbound_documents_enabled, inbound_document_codes, inbound_signature_delivery_ids, send_welcome_with_documents, welcome_message_extra, daily_summary_enabled, require_project_on_clock_in, updated_at, clock_exit_reminder_minutes) FROM stdin;
bdd57572-5518-48c0-9e27-b9f2c23591de	f	\N	f	\N	t	["dni", "photo", "driving_license", "legal_terms"]	[]	t	\N	t	f	2026-06-14 17:39:46.670166	\N
cbbf551f-87c4-47f4-aa8b-cd20e7036a61	f	5	f	\N	t	[]	[]	t	\N	f	f	2026-06-18 07:44:14.045843	15
cf26f84d-f21f-4138-a024-e6ce33797ffd	f	\N	f	\N	t	["dni", "photo", "driving_license", "legal_terms"]	[]	t	\N	t	f	2026-06-10 19:34:50.228262	\N
951a449d-5f92-49c5-aec3-b3de06c44bcf	t	5	f	\N	t	["dni", "photo", "driving_license", "legal_terms"]	[]	t	\N	t	t	2026-06-15 14:54:30.616972	10
\.


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.companies (id, tenant_id, name, tax_id, is_active, legal_name, billing_email, billing_phone, billing_address, billing_city, billing_postal_code, billing_province, billing_country, created_at) FROM stdin;
f13fda9a-7d23-4597-86e9-2bcfadc2c677	cf26f84d-f21f-4138-a024-e6ce33797ffd	Empresa Principal	\N	t	Cuenta Demo	\N	\N	\N	\N	\N	\N	ES	2026-05-25 18:50:53.607425
ec0da4d5-072b-4ede-85d3-439c47fc7e44	951a449d-5f92-49c5-aec3-b3de06c44bcf	Jjac	B9000	t	Jonatan Luna	info@jjac.es	647409876	\N	\N	\N	\N	ES	2026-05-25 20:02:55.912159
bb7211f4-1102-4865-a44c-cebcf8f075c8	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	Puerta Sevilla	B90000092	t	Puerta Sevilla inmobiliaria	benito.barrios@dealerbest.com	685 08 41 65	\N	\N	\N	\N	ES	2026-06-07 16:55:41.56438
376289a5-f76d-42e5-a07e-d266ec828caa	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	MORRIÑA REAL ESTATE		t	\N	\N	\N	\N	\N	\N	\N	ES	2026-06-12 11:31:00.425438
35694ea1-39a1-4a90-99c9-2616c4b1adf1	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	MOTOLO CAPITAL		t	\N	\N	\N	\N	\N	\N	\N	ES	2026-06-12 11:31:20.671386
4553c7c5-ec1f-4273-8053-4498eccd7f63	bdd57572-5518-48c0-9e27-b9f2c23591de	prueba liaño	B90000092	t	prueba liaño	lblr81@gmail.com	679324504	\N	\N	\N	\N	ES	2026-06-14 17:37:01.234437
78fe1d81-289a-44c5-9897-eb3a2689ae56	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	prueba liaño 2	B90000093	t	prueba liaño 2	lblr81@gmail.com	679324504	\N	\N	\N	\N	ES	2026-06-14 17:45:13.451827
\.


--
-- Data for Name: departments; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.departments (id, work_center_id, name, code, is_active, created_at) FROM stdin;
73ff80cf-66fa-4885-8abd-4801c5f5b49f	155b210a-0a96-4203-bfb2-48ce0ef491df	General	GEN	t	2026-05-25 19:03:03.388045
ddcdd2d8-893f-4b2a-867a-26c03d05e6fe	f62ff184-1e70-4827-b5ea-48762c5cac3f	General	GEN	t	2026-05-25 20:02:55.917089
45b53596-936f-4586-b26b-af5626a73aa3	c96ce44c-4fd6-4cdc-bbe6-da31bd2d1145	General	GEN	t	2026-06-07 16:55:41.56952
e738c1aa-41c9-4559-bea0-6353c9c04443	9e76d734-8db1-4d2c-a4ee-b45885874e87	General	GEN	t	2026-06-12 14:33:08.670007
64088782-96cb-4c26-8f6f-6cf266c1d9ce	2eedf1c4-ff1b-4900-8765-7d7a58437d32	General	GEN	t	2026-06-12 14:33:08.675119
e55c756c-a66d-480c-98f0-953a55a7010c	d29f83ef-5aba-43a2-90a8-2b8465d08c12	General	GEN	t	2026-06-14 17:37:01.23987
8d68c922-746b-474d-aa26-a844004d677e	17c2163b-2823-4aab-b2d3-71eecf1e77e0	General	GEN	t	2026-06-14 17:45:13.456442
\.


--
-- Data for Name: discounts; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.discounts (id, code, name, description, discount_type, value, valid_from, valid_until, pricing_plan_id, is_active, created_at, updated_at, ls_discount_id) FROM stdin;
9f9cb70d-54c2-403f-9140-0cc61b2ef3c4	DTO100	Descuento 100%	\N	PERCENT	100	2026-06-12	2026-12-31	\N	t	2026-06-12 14:36:13.667975	2026-06-14 15:21:30.591932	1039876
0babd662-7bde-4cfa-a582-f3fc738d8996	PIONERO	Dto pioneros	\N	PERCENT	90	2026-06-12	2027-05-31	\N	t	2026-06-12 14:36:45.176929	2026-06-14 15:21:38.693283	1039877
\.


--
-- Data for Name: document_deliveries; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.document_deliveries (id, tenant_id, company_id, employee_id, document_type_id, file_path, file_name, document_type, title, expires_at, sent_at, acknowledged_at, acknowledgment_text, requires_acknowledgment, created_at) FROM stdin;
f334b2ca-d7ac-4797-bf03-345b79d8b789	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	f41acab0-d7a1-4441-942b-69664ceb9d3b	15a6f038-6f2f-4ea1-bfc8-65da412685f1	/app/uploads/ddf10ea6-2580-4881-b246-4aa3139d7917_bdc23510-6041-435c-855d-15ca5e524806_1780678129-e0101990-dea2-405c-a4b6-eb6d7a35aae3.jpeg	bdc23510-6041-435c-855d-15ca5e524806_1780678129-e0101990-dea2-405c-a4b6-eb6d7a35aae3.jpeg	otro	Foto del empleado	\N	2026-06-05 16:50:59.726221	\N	\N	f	2026-06-05 16:48:55.196989
86bcf881-fda1-4013-969c-502dbe80c467	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	ef3409d9-798e-468c-9934-0b80e1ff7dc2	15a6f038-6f2f-4ea1-bfc8-65da412685f1	/app/uploads/051e10ac-766f-4580-9ecc-6402662bf73d_alcurro_trans.png	alcurro_trans.png	otro	Foto del empleado	\N	\N	\N	\N	f	2026-06-07 09:44:43.909126
070213a7-5aad-4269-9bd3-93dd897463c3	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	f41acab0-d7a1-4441-942b-69664ceb9d3b	\N	/app/uploads/legal/89da83de-81f8-4735-90c3-35b2d948a774_legal_Normativa_interna_y_uso_de_medios_digita_v1.pdf	legal_Normativa_interna_y_uso_de_medios_digita_v1.pdf	legal_acceptance	Aceptación: Normativa interna y uso de medios digitales (v1)	\N	\N	\N	\N	f	2026-06-07 10:04:21.034195
\.


--
-- Data for Name: document_delivery_tags; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.document_delivery_tags (id, document_delivery_id, tag_id) FROM stdin;
\.


--
-- Data for Name: document_expiry_notification_logs; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.document_expiry_notification_logs (id, tenant_id, document_delivery_id, days_before, channel, recipient, success, detail, sent_at) FROM stdin;
\.


--
-- Data for Name: document_notification_settings; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.document_notification_settings (tenant_id, enabled, days_before, channel_whatsapp, channel_email, notify_employee, notify_managers, extra_emails, updated_at) FROM stdin;
cf26f84d-f21f-4138-a024-e6ce33797ffd	f	30,7,1	t	t	t	t	\N	2026-05-25 18:50:56.428674
951a449d-5f92-49c5-aec3-b3de06c44bcf	f	30,7,1	t	t	t	t	\N	2026-05-26 10:16:06.246001
cbbf551f-87c4-47f4-aa8b-cd20e7036a61	f	30,7,1	t	t	t	t	\N	2026-06-07 17:16:11.310824
bdd57572-5518-48c0-9e27-b9f2c23591de	f	30,7,1	t	t	t	t	\N	2026-06-14 17:42:40.747456
deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	f	30,7,1	t	t	t	t	\N	2026-06-14 17:53:18.784217
\.


--
-- Data for Name: document_tags; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.document_tags (id, tenant_id, name, color, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: document_types; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.document_types (id, tenant_id, code, name, description, is_active, sort_order, created_at) FROM stdin;
d9427190-833e-4ace-809f-4d26fb480eae	cf26f84d-f21f-4138-a024-e6ce33797ffd	nomina	Nómina	\N	t	0	2026-05-25 18:50:56.341875
c53198c6-9160-46bc-921d-28e3b46a748a	cf26f84d-f21f-4138-a024-e6ce33797ffd	contrato	Contrato	\N	t	1	2026-05-25 18:50:56.341875
f371d83d-fd8f-4607-8570-8111dea0aa78	cf26f84d-f21f-4138-a024-e6ce33797ffd	certificado	Certificado	\N	t	2	2026-05-25 18:50:56.341875
d0449099-6097-438a-b67e-e6709a6e5e64	cf26f84d-f21f-4138-a024-e6ce33797ffd	comunicado	Comunicado	\N	t	3	2026-05-25 18:50:56.341875
5c47897d-3440-4b80-8501-bed8cefd8b57	cf26f84d-f21f-4138-a024-e6ce33797ffd	otro	Otro	\N	t	4	2026-05-25 18:50:56.341875
a12cde1c-b2e0-433b-8e6f-2f47c480696d	951a449d-5f92-49c5-aec3-b3de06c44bcf	nomina	Nómina	\N	t	0	2026-05-26 10:16:06.149476
0e8b4edd-788a-41a4-bfb4-da22cb2076d5	951a449d-5f92-49c5-aec3-b3de06c44bcf	contrato	Contrato	\N	t	1	2026-05-26 10:16:06.149476
6ec7a6db-7585-4c75-9d11-65d83d5c2c70	951a449d-5f92-49c5-aec3-b3de06c44bcf	certificado	Certificado	\N	t	2	2026-05-26 10:16:06.149476
bb143a99-82ce-4c96-933e-b0b01be2de05	951a449d-5f92-49c5-aec3-b3de06c44bcf	comunicado	Comunicado	\N	t	3	2026-05-26 10:16:06.149476
15a6f038-6f2f-4ea1-bfc8-65da412685f1	951a449d-5f92-49c5-aec3-b3de06c44bcf	otro	Otro	\N	t	4	2026-05-26 10:16:06.149476
c0564d3f-18c9-49b5-9d31-41a6ad39ea99	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	nomina	Nómina	\N	t	0	2026-06-07 17:16:11.220099
72f3651c-4281-408c-9d12-775fcc7d75c6	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	contrato	Contrato	\N	t	1	2026-06-07 17:16:11.220099
db1c91bf-6105-4b57-a1eb-c91201bd7a51	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	certificado	Certificado	\N	t	2	2026-06-07 17:16:11.220099
8a0dab72-b258-4e5f-87fa-8603bccc069e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	comunicado	Comunicado	\N	t	3	2026-06-07 17:16:11.220099
189070e5-9181-48c2-8c74-f033400339be	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	otro	Otro	\N	t	4	2026-06-07 17:16:11.220099
17b3ecf7-6a74-441c-9c4f-6988ff894b51	bdd57572-5518-48c0-9e27-b9f2c23591de	nomina	Nómina	\N	t	0	2026-06-14 17:42:40.648955
fc5a98b6-f71a-4362-9085-7a62d2aca19a	bdd57572-5518-48c0-9e27-b9f2c23591de	contrato	Contrato	\N	t	1	2026-06-14 17:42:40.648955
c09c7386-e7ec-40c6-a723-9ad2f1035b4f	bdd57572-5518-48c0-9e27-b9f2c23591de	certificado	Certificado	\N	t	2	2026-06-14 17:42:40.648955
dfe9ed51-48d0-4c6f-9efe-bb8cce69c541	bdd57572-5518-48c0-9e27-b9f2c23591de	comunicado	Comunicado	\N	t	3	2026-06-14 17:42:40.648955
db62e21d-0e66-4f6e-8978-c4637c4e7090	bdd57572-5518-48c0-9e27-b9f2c23591de	otro	Otro	\N	t	4	2026-06-14 17:42:40.648955
c21134a8-cf3b-4f88-ad56-9796d4d4f50a	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	nomina	Nómina	\N	t	0	2026-06-14 17:53:18.690368
aa3945e1-9e55-47f2-8dc4-768cd22c3e05	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	contrato	Contrato	\N	t	1	2026-06-14 17:53:18.690368
4bd43f58-4da2-4cce-ae61-112e3f3a8962	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	certificado	Certificado	\N	t	2	2026-06-14 17:53:18.690368
0a3e2cea-0f24-412b-9b9a-6fead8c3e0ac	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	comunicado	Comunicado	\N	t	3	2026-06-14 17:53:18.690368
87b7147d-8ac5-4c06-a9c9-cdaa1b21f206	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	otro	Otro	\N	t	4	2026-06-14 17:53:18.690368
\.


--
-- Data for Name: employee_groups; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.employee_groups (id, employee_id, group_id, created_at) FROM stdin;
90129305-e9d1-4038-90ef-2d94faa98b6e	a1111fc5-3fc9-44fb-b346-d5e39282b83d	12173caf-aacc-4871-83dd-a9f498f61d03	2026-05-25 19:19:33.551471
2d4b8cb7-7d7c-496b-b079-188cf8fb409f	7517b468-f330-4b1d-bb41-101bb81efec2	b58c39c5-473e-4dd2-9d8c-1d6af0094d5c	2026-05-25 19:19:33.553823
ddbd414e-5867-41f6-8dc3-b8380ecb75e2	ef3409d9-798e-468c-9934-0b80e1ff7dc2	6735b40b-a4ed-4336-8776-b65f763a3531	2026-06-04 17:27:13.967115
08111994-08cc-40a7-bab0-59805303699f	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	70c7abf5-5e5b-4f3a-86c7-b75c1621dda6	2026-06-06 18:02:53.828738
a88512bf-117e-473c-839c-6dc62cd7a4f0	f41acab0-d7a1-4441-942b-69664ceb9d3b	70c7abf5-5e5b-4f3a-86c7-b75c1621dda6	2026-06-06 20:31:53.080294
3c6ede41-a3c3-4b6e-86ab-71776f507c6b	941a5698-80fc-41ec-87c7-1fe4fa28ba75	819b1856-3f23-4e88-9783-83f0fb7f60b6	2026-06-07 16:55:41.88553
aa6847cb-1ad7-4887-abc8-b32353d2f81d	2e344a27-169d-44fa-8151-0e643749dc33	4cd88a84-e0de-4fde-a559-dec3836a46be	2026-06-12 11:29:43.010505
c207db85-6093-44b4-b8ee-565709399d30	e5e24f2f-86ec-4321-8853-e394a494630e	4cd88a84-e0de-4fde-a559-dec3836a46be	2026-06-12 11:30:16.649088
a29f6db8-194e-49d5-999b-3ed27426ffae	e5e24f2f-86ec-4321-8853-e394a494630e	819b1856-3f23-4e88-9783-83f0fb7f60b6	2026-06-12 11:30:16.649342
5468f2bc-8fb3-43a8-abc8-4525afd0ea37	c7f9b894-5791-41a8-b488-cc64c6eafc22	4cd88a84-e0de-4fde-a559-dec3836a46be	2026-06-12 17:04:07.503012
76a937b0-220d-450d-b44d-ff1ff4e8156f	306eeb83-734b-42f3-b556-72d2f3ff15be	f8873d0b-8d96-4288-8b01-59eb597ebe00	2026-06-14 17:37:01.574274
460c8b5a-9581-474e-82a3-dc460a56c076	c9e697a9-48eb-4f8d-a9ba-d9b1be9ccbd9	4d4dabfe-67f6-4228-b32c-0b68036c52d3	2026-06-14 17:45:13.775965
c31af4aa-0c4e-4986-bd94-30bdba6b1f5c	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	4cd88a84-e0de-4fde-a559-dec3836a46be	2026-06-17 09:47:58.456289
3b08ab12-30d3-4463-a0e6-23b664b91112	c3136edf-351e-4329-8050-720ecd216410	4cd88a84-e0de-4fde-a559-dec3836a46be	2026-06-18 08:17:33.795892
2af8f883-2675-4426-bdaa-0b70a1a2d753	c3136edf-351e-4329-8050-720ecd216410	819b1856-3f23-4e88-9783-83f0fb7f60b6	2026-06-18 08:17:33.796026
\.


--
-- Data for Name: employee_inbound_documents; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.employee_inbound_documents (id, employee_id, document_code, status, document_delivery_id, signature_envelope_id, received_at, notes, created_at) FROM stdin;
75057b5f-1fb5-4128-82ea-6d1f9fdcd227	f41acab0-d7a1-4441-942b-69664ceb9d3b	dni	pending	\N	\N	\N	\N	2026-06-05 06:46:19.332747
73764cc0-71e0-43f8-8a7c-2f6be55af71e	f41acab0-d7a1-4441-942b-69664ceb9d3b	driving_license	pending	\N	\N	\N	\N	2026-06-05 06:46:19.337153
87538705-770e-4b05-9e51-60a660ce9c94	f41acab0-d7a1-4441-942b-69664ceb9d3b	legal_terms	pending	\N	\N	\N	\N	2026-06-05 06:46:19.338616
04d6bc64-2832-4121-8ef2-fd3dd52fd45d	ef3409d9-798e-468c-9934-0b80e1ff7dc2	dni	pending	\N	\N	\N	\N	2026-06-05 08:17:07.154991
5d405bb5-f44f-47f1-8dd2-c83453a526a8	ef3409d9-798e-468c-9934-0b80e1ff7dc2	driving_license	pending	\N	\N	\N	\N	2026-06-05 08:17:07.161399
3def4598-e028-4984-a1c6-f80220027135	ef3409d9-798e-468c-9934-0b80e1ff7dc2	legal_terms	pending	\N	\N	\N	\N	2026-06-05 08:17:07.16322
766d702e-baff-4aa0-bec8-5f03cb534808	f41acab0-d7a1-4441-942b-69664ceb9d3b	photo	received	f334b2ca-d7ac-4797-bf03-345b79d8b789	\N	2026-06-05 16:48:55.202722	\N	2026-06-05 06:46:19.335595
c9aa7cc7-c998-4c15-9eb9-9e2e36015620	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	dni	pending	\N	\N	\N	\N	2026-06-06 18:02:53.207031
04edd3de-8f7e-446f-bd5c-23ba5b892db9	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	photo	pending	\N	\N	\N	\N	2026-06-06 18:02:53.211681
e275d76a-95d7-4244-9353-6517c0241ab8	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	driving_license	pending	\N	\N	\N	\N	2026-06-06 18:02:53.213899
3d440532-68c0-4691-9968-4fbd9a537a60	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	legal_terms	pending	\N	\N	\N	\N	2026-06-06 18:02:53.215882
f52b91af-0599-419c-a2dc-017b466fb0cb	ef3409d9-798e-468c-9934-0b80e1ff7dc2	photo	received	86bcf881-fda1-4013-969c-502dbe80c467	\N	2026-06-07 09:44:43.9124	\N	2026-06-05 08:17:07.159482
0ebda24b-d98f-4c65-bcad-5caa54178783	941a5698-80fc-41ec-87c7-1fe4fa28ba75	dni	pending	\N	\N	\N	\N	2026-06-07 21:18:11.865518
991a8d98-a77e-4c09-8e6d-a688887f9d7c	941a5698-80fc-41ec-87c7-1fe4fa28ba75	photo	pending	\N	\N	\N	\N	2026-06-07 21:18:11.868571
fae566e4-4d8c-4358-b5d1-7b165eaf8316	941a5698-80fc-41ec-87c7-1fe4fa28ba75	driving_license	pending	\N	\N	\N	\N	2026-06-07 21:18:11.870069
726395ae-7b7c-4779-8ba7-e9270697ee1d	941a5698-80fc-41ec-87c7-1fe4fa28ba75	legal_terms	pending	\N	\N	\N	\N	2026-06-07 21:18:11.87148
b1cbc444-fc1a-4ace-8b65-c0c3c331cf56	e5e24f2f-86ec-4321-8853-e394a494630e	dni	pending	\N	\N	\N	\N	2026-06-11 14:07:27.599481
c67e9d5f-cf62-4f91-8e00-2fd28e12fbef	e5e24f2f-86ec-4321-8853-e394a494630e	photo	pending	\N	\N	\N	\N	2026-06-11 14:07:27.602036
74a577e2-e061-478c-ab27-a7fefe87999b	e5e24f2f-86ec-4321-8853-e394a494630e	driving_license	pending	\N	\N	\N	\N	2026-06-11 14:07:27.603859
318d9665-1934-4774-9ea2-ccc3bf49bbb2	e5e24f2f-86ec-4321-8853-e394a494630e	legal_terms	pending	\N	\N	\N	\N	2026-06-11 14:07:27.605611
f55fb878-5a3a-4f64-afa7-39765a5e41af	c3136edf-351e-4329-8050-720ecd216410	dni	pending	\N	\N	\N	\N	2026-06-11 14:12:14.695559
04af9c64-3e1a-48a8-a39c-56b69bb1e2a6	c3136edf-351e-4329-8050-720ecd216410	photo	pending	\N	\N	\N	\N	2026-06-11 14:12:14.69741
6c796c1c-36b3-4b1c-a833-1534e8907ec3	2e344a27-169d-44fa-8151-0e643749dc33	dni	pending	\N	\N	\N	\N	2026-06-12 11:20:43.451492
672b53ce-9664-46ac-8dc5-b1f6e974e0cc	2e344a27-169d-44fa-8151-0e643749dc33	photo	pending	\N	\N	\N	\N	2026-06-12 11:20:43.453255
d797c0c7-afd3-4d2a-9536-b29c7c789fc2	c7f9b894-5791-41a8-b488-cc64c6eafc22	dni	pending	\N	\N	\N	\N	2026-06-12 16:32:29.222839
c70319cf-6a6a-43c4-95df-77a1fee4a290	c7f9b894-5791-41a8-b488-cc64c6eafc22	photo	pending	\N	\N	\N	\N	2026-06-12 16:32:29.225519
e6f69351-f5d1-4b17-8f79-b0fc336faafa	a1111fc5-3fc9-44fb-b346-d5e39282b83d	dni	pending	\N	\N	\N	\N	2026-06-12 18:12:56.362159
656022a0-acfa-4fa4-86e0-d9708c1ec08b	a1111fc5-3fc9-44fb-b346-d5e39282b83d	photo	pending	\N	\N	\N	\N	2026-06-12 18:12:56.365771
2c867936-95fe-412d-9f70-73009ca184da	a1111fc5-3fc9-44fb-b346-d5e39282b83d	driving_license	pending	\N	\N	\N	\N	2026-06-12 18:12:56.367386
07c4648e-fb13-41e5-9cad-de4135528aa5	a1111fc5-3fc9-44fb-b346-d5e39282b83d	legal_terms	pending	\N	\N	\N	\N	2026-06-12 18:12:56.368847
5675e698-2706-4b5b-8584-58716158abe0	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	dni	pending	\N	\N	\N	\N	2026-06-17 07:32:02.576312
9369593b-a03e-45eb-ae8b-342d1d1f9617	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	photo	pending	\N	\N	\N	\N	2026-06-17 07:32:02.579236
\.


--
-- Data for Name: employee_leave_balances; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.employee_leave_balances (id, employee_id, leave_type_id, total_days, notes, created_at) FROM stdin;
21a3366b-fa7a-44f3-b6ee-4a2721d8de43	f41acab0-d7a1-4441-942b-69664ceb9d3b	325ecbf1-c3e2-489d-8afa-90bc7a36c636	5	\N	2026-06-07 08:12:46.83353
d60caab3-dc93-4652-8f31-18cce3c0d427	c3136edf-351e-4329-8050-720ecd216410	0a6ffda0-682a-43d3-ba5a-146d7c4a93f6	2	\N	2026-06-12 11:13:50.58383
\.


--
-- Data for Name: employees; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.employees (id, company_id, department_id, phone, email, full_name, id_document, employee_code, role, supervisor_id, vacation_days_balance, is_active, password_hash, shift_configuration_id, work_start_time, work_end_time, work_days, work_schedule_blocks, work_schedule_periods, rotating_shift, weekly_hours, welcome_sent_at, last_clock_reminder_at, created_at, updated_at, avatar_delivery_id, job_title, last_exit_reminder_at, last_incident_reminder_at) FROM stdin;
b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	ec0da4d5-072b-4ede-85d3-439c47fc7e44	\N	699999998	info@jjac.es	Info Jjac	\N	ADM002	tenant_admin	\N	22	t	$2b$12$9fJpq0ELqtvjmpoc4WbyQe8ZPEKhH1oKNOMbehS9msBH4m/KgT06u	\N	\N	\N	[0, 1, 2, 3, 4]	[]	[]	f	\N	\N	\N	2026-06-05 06:41:52.87579	2026-06-05 06:41:52.87579	\N	\N	\N	\N
6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	bb7211f4-1102-4865-a44c-cebcf8f075c8	45b53596-936f-4586-b26b-af5626a73aa3	34667293394	carmengala90@gmail.com	CARMEN GALA SERRANO	30259297V	EMP-005	EMPLOYEE	\N	22	t	\N	\N	09:30:00	17:30:00	[0, 1, 2, 3, 4]	[{"work_days": [0, 1, 2, 3, 4], "work_start_time": "09:30:00", "work_end_time": "17:30:00", "break_minutes": 0}]	[{"valid_from": "2026-01-01", "valid_to": null, "blocks": [{"work_days": [0, 1, 2, 3, 4], "slots": [{"work_start_time": "09:30:00", "work_end_time": "17:30:00", "break_minutes": 0}]}]}]	f	\N	2026-06-17 07:32:03.466122	2026-06-19 07:35:16.206013	2026-06-17 07:32:02.562897	2026-06-17 09:47:58.41397	\N	\N	2026-06-19 15:45:19.398778	\N
ef3409d9-798e-468c-9934-0b80e1ff7dc2	ec0da4d5-072b-4ede-85d3-439c47fc7e44	ddcdd2d8-893f-4b2a-867a-26c03d05e6fe	699999999	admin@jjac.es	Admin Jjac	\N	ADM001	tenant_admin	\N	22	t	$2b$12$9fJpq0ELqtvjmpoc4WbyQe8ZPEKhH1oKNOMbehS9msBH4m/KgT06u	\N	\N	\N	[0, 1, 2, 3, 4]	[]	[]	f	\N	\N	\N	2026-06-04 17:26:52.105372	2026-06-04 17:26:52.105372	86bcf881-fda1-4013-969c-502dbe80c467	\N	\N	\N
c7f9b894-5791-41a8-b488-cc64c6eafc22	bb7211f4-1102-4865-a44c-cebcf8f075c8	45b53596-936f-4586-b26b-af5626a73aa3	34679324504	lblr81@gmail.com	Lucía	28811323M	EMP-004	EMPLOYEE	\N	22	f	$2b$12$z4fRSgOv9NvCG5o2tmFwaOAcMca/fkCcT2bjXrl6zOzkmYo9dZBAm	\N	09:00:00	14:00:00	[0, 1, 2, 3]	[{"work_days": [0, 1, 2, 3], "work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0}, {"work_days": [4], "work_start_time": "08:00:00", "work_end_time": "15:00:00", "break_minutes": 0}]	[{"valid_from": "2026-01-01", "valid_to": null, "blocks": [{"work_days": [0, 1, 2, 3], "slots": [{"work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0}, {"work_start_time": "16:00:00", "work_end_time": "18:00:00", "break_minutes": 0}]}, {"work_days": [4], "slots": [{"work_start_time": "08:00:00", "work_end_time": "15:00:00", "break_minutes": 0}]}]}]	f	\N	2026-06-12 16:32:29.690253	2026-06-12 16:36:33.891536	2026-06-12 16:32:28.923685	2026-06-12 17:39:42.60372	\N	\N	\N	\N
c9e697a9-48eb-4f8d-a9ba-d9b1be9ccbd9	78fe1d81-289a-44c5-9897-eb3a2689ae56	\N	679324504	lblr81@gmail.com	Lucia prueba 2	\N	ADM001	tenant_admin	\N	22	t	$2b$12$OrmsVEIaBsIn8add9pjRRuWKv3Y4XifN6JMBCQrwn3a2tmHLACxWC	\N	\N	\N	[0, 1, 2, 3, 4]	[]	[]	f	\N	\N	\N	2026-06-14 17:45:13.767856	2026-06-14 17:45:13.767876	\N	\N	\N	\N
941a5698-80fc-41ec-87c7-1fe4fa28ba75	bb7211f4-1102-4865-a44c-cebcf8f075c8	\N	685 08 41 65	benito.barrios@dealerbest.com	Benito	\N	ADM001	tenant_admin	\N	22	t	$2b$12$QaWUZcD3JllDgb4Ul0hTzuURqgYuKO91tztI1f0DSwbP2mgVZHXpO	\N	\N	\N	[0, 1, 2, 3, 4]	[]	[]	f	\N	2026-06-07 21:18:12.530791	\N	2026-06-07 16:55:41.875559	2026-06-07 16:55:41.875581	\N	\N	\N	\N
7517b468-f330-4b1d-bb41-101bb81efec2	f13fda9a-7d23-4597-86e9-2bcfadc2c677	\N	34600000003	inspector@empresa.local	Inspector Trabajo	\N	INS001	LABOR_INSPECTOR	\N	0	t	$2b$12$QPZafNF1bJ7jLhFKUJ8.l.v.N8Fr2tetr4RuAaEjG.J2Ng4tkcqoO	\N	\N	\N	[0, 1, 2, 3, 4]	[]	[]	f	\N	\N	\N	2026-05-25 19:19:33.53812	2026-06-12 17:10:23.351425	\N	\N	\N	\N
a1111fc5-3fc9-44fb-b346-d5e39282b83d	f13fda9a-7d23-4597-86e9-2bcfadc2c677	\N	34600000002	supervisor@empresa.local	María García (Supervisor)	\N	SUP001	EMPLOYEE	\N	25	t	$2b$12$XmqUKolQciUtIiDR7LU5/.c093Qg4A62w..zXWh14Cg3bGynmracm	\N	\N	\N	[0, 1, 2, 3, 4]	[]	[]	f	\N	2026-06-12 18:12:57.088807	\N	2026-05-25 19:19:33.2539	2026-05-25 19:19:33.253918	\N	\N	\N	\N
306eeb83-734b-42f3-b556-72d2f3ff15be	4553c7c5-ec1f-4273-8053-4498eccd7f63	\N	679324504	lblr81@gmail.com	Lucía Liaño	\N	ADM001	tenant_admin	\N	22	t	$2b$12$3lZ7uWTToM3jbzMnRO6K1u3NGhseWwARlhFX3hZ5ARZrU9kr8ErSW	\N	\N	\N	[0, 1, 2, 3, 4]	[]	[]	f	\N	\N	\N	2026-06-14 17:37:01.562173	2026-06-14 17:37:01.562232	\N	\N	\N	\N
07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	ec0da4d5-072b-4ede-85d3-439c47fc7e44	ddcdd2d8-893f-4b2a-867a-26c03d05e6fe	34647409876	beni4041@gmail.com	Luna	28123123J	EMP-002	EMPLOYEE	\N	22	t	$2b$12$gIpRg3aBvqkeMIo03VHPgOyLudbUEHxYrw9IBJOxi2e7RnNpRbUrq	\N	07:00:00	15:00:00	[0, 1, 2, 3, 4]	[{"work_days": [0, 1, 2, 3, 4], "work_start_time": "07:00:00", "work_end_time": "15:00:00", "break_minutes": 0}]	[{"valid_from": "2026-01-01", "valid_to": null, "blocks": [{"work_days": [0, 1, 2, 3, 4], "slots": [{"work_start_time": "07:00:00", "work_end_time": "15:00:00", "break_minutes": 0}]}]}]	f	\N	2026-06-06 18:02:53.782965	2026-06-19 05:05:14.059326	2026-06-06 18:02:52.896448	2026-06-06 18:02:52.896452	\N	\N	2026-06-19 13:10:18.329896	\N
f41acab0-d7a1-4441-942b-69664ceb9d3b	ec0da4d5-072b-4ede-85d3-439c47fc7e44	ddcdd2d8-893f-4b2a-867a-26c03d05e6fe	34624230960	beni4041@gmail.com	Benito	28778763J	EMP-001	EMPLOYEE	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	22	t	$2b$12$f77NFM62At.yiEzAFYy95u8inoZdtbR2GUaCXQLwzls2SAli9hHiW	\N	09:00:00	14:00:00	[0, 1, 2, 3]	[{"work_days": [0, 1, 2, 3], "work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0}, {"work_days": [4], "work_start_time": "08:00:00", "work_end_time": "15:00:00", "break_minutes": 0}]	[{"valid_from": "2026-01-01", "valid_to": null, "blocks": [{"work_days": [0, 1, 2, 3], "slots": [{"work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0}, {"work_start_time": "16:00:00", "work_end_time": "18:00:00", "break_minutes": 0}]}, {"work_days": [4], "slots": [{"work_start_time": "08:00:00", "work_end_time": "15:00:00", "break_minutes": 0}]}]}]	f	\N	2026-06-05 06:46:20.07875	2026-06-19 06:05:14.678602	2026-06-05 06:46:19.032884	2026-06-06 20:31:53.040906	f334b2ca-d7ac-4797-bf03-345b79d8b789	administrativo	2026-06-19 13:10:17.934563	\N
e5e24f2f-86ec-4321-8853-e394a494630e	bb7211f4-1102-4865-a44c-cebcf8f075c8	45b53596-936f-4586-b26b-af5626a73aa3	34655881129	cdocobo@gmail.com	Carmen Docobo	44812035P	EMP-001	tenant_admin	\N	22	t	$2b$12$w0QzBGbAdIiZYUzNW.x3Bue08ZWEOLMiPjYuTES37TYX4TBbmiD2S	\N	09:00:00	14:00:00	[0, 1, 2, 3, 4]	[{"work_days": [0, 1, 2, 3, 4], "work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0}]	[{"valid_from": "2026-01-01", "valid_to": null, "blocks": [{"work_days": [0, 1, 2, 3, 4], "slots": [{"work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0}]}]}]	f	\N	2026-06-11 14:07:28.322287	2026-06-19 07:05:15.691605	2026-06-11 14:07:27.301757	2026-06-12 11:30:16.60532	\N	\N	2026-06-17 12:19:55.822854	\N
2e344a27-169d-44fa-8151-0e643749dc33	bb7211f4-1102-4865-a44c-cebcf8f075c8	45b53596-936f-4586-b26b-af5626a73aa3	34633859349	jairosfc@gmail.com	Jairo Pineda Zapata	28633647G	EMP-003	EMPLOYEE	e5e24f2f-86ec-4321-8853-e394a494630e	22	t	\N	\N	09:00:00	14:00:00	[0, 1, 2, 3, 4]	[{"work_days": [0, 1, 2, 3, 4], "work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0}]	[{"valid_from": "2026-01-01", "valid_to": null, "blocks": [{"work_days": [0, 1, 2, 3, 4], "slots": [{"work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0}, {"work_start_time": "17:00:00", "work_end_time": "20:00:00", "break_minutes": 0}]}]}]	f	\N	2026-06-12 11:20:44.043152	2026-06-19 07:05:15.32704	2026-06-12 11:20:43.44417	2026-06-12 11:29:42.968554	\N	\N	2026-06-19 18:15:20.515673	\N
c3136edf-351e-4329-8050-720ecd216410	35694ea1-39a1-4a90-99c9-2616c4b1adf1	64088782-96cb-4c26-8f6f-6cf266c1d9ce	34624602500	mdgarron@gmail.com	María Diaz Garrón	30254529F	EMP-002	tenant_admin	e5e24f2f-86ec-4321-8853-e394a494630e	22	t	$2b$12$KUAIrI2Nz47/qYE41VRwFul0pIoY0OBnZw/aeDYdhMvEY5hW0/I2G	\N	09:30:00	14:00:00	[0, 1, 2, 3, 4]	[{"work_days": [0, 1, 2, 3, 4], "work_start_time": "09:30:00", "work_end_time": "14:00:00", "break_minutes": 0}]	[{"valid_from": "2026-01-01", "valid_to": null, "blocks": [{"work_days": [0, 1, 2, 3, 4], "slots": [{"work_start_time": "09:30:00", "work_end_time": "14:00:00", "break_minutes": 0}]}]}]	f	\N	2026-06-11 14:12:15.422911	2026-06-18 07:05:05.394303	2026-06-11 14:12:14.401247	2026-06-18 08:17:33.755035	\N	\N	2026-06-17 12:19:55.104504	\N
\.


--
-- Data for Name: group_templates; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.group_templates (id, name, description, permissions, is_system, sort_order, created_at) FROM stdin;
a6026292-2d7d-4308-aff1-531df481d569	Administradores de cuenta	Control total del tenant: empresas, centros, departamentos y configuración	["clock_ins.read", "clock_ins.write", "companies.read", "companies.write", "departments.read", "departments.write", "documents.read", "documents.write", "employees.delete", "employees.read", "employees.write", "gowa.manage", "groups.read", "groups.write", "leave.approve", "leave.read", "leave.write", "settings.read", "settings.write", "shifts.read", "shifts.write", "tenant.billing", "tenant.read", "tenant.write", "work_centers.read", "work_centers.write"]	t	0	2026-05-25 19:03:03.366863
a596b852-fbc8-40fa-8cfd-1f3eeeb4659d	Responsables	Gestión de equipos: empleados, fichajes, vacaciones y turnos en su ámbito	["clock_ins.read", "clock_ins.write", "companies.read", "departments.read", "documents.read", "documents.write", "employees.read", "employees.write", "groups.read", "leave.approve", "leave.read", "leave.write", "shifts.read", "shifts.write", "tenant.read", "work_centers.read"]	t	1	2026-05-25 19:03:03.370559
a200c68f-d24d-42e7-b3d9-c80ea116c424	Empleados con panel	Consulta de fichajes y vacaciones propias	["breaks.create_own", "breaks.read_own", "clock_ins.create_own", "clock_ins.read_own", "documents.read_own", "leave.create_own", "leave.read_own", "leave.update_own", "legal.read", "legal.read_own", "legal.update_own", "signatures.read_own"]	t	2	2026-05-25 19:03:03.372077
cf089846-fb10-4582-9947-bcbe8b00cc2b	Inspector de Trabajo	Solo lectura en todos los módulos	["clock_ins.read", "companies.read", "departments.read", "documents.read", "employees.read", "groups.read", "leave.approve", "leave.read", "settings.read", "shifts.read", "tenant.read", "work_centers.read"]	t	3	2026-05-25 19:03:03.373338
\.


--
-- Data for Name: inbound_pending_uploads; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.inbound_pending_uploads (employee_id, file_path, filename, whatsapp_message_id, created_at) FROM stdin;
\.


--
-- Data for Name: incident_auto_rules; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.incident_auto_rules (tenant_id, late_entrada_enabled, late_entrada_grace_minutes, late_entrada_notify_whatsapp, late_entrada_require_justification, updated_at, missing_clock_in_enabled, missing_clock_in_hours, missing_clock_in_notify_whatsapp, missing_clock_in_require_justification, missing_clock_out_enabled, missing_clock_out_hours, missing_clock_out_notify_whatsapp, missing_clock_out_require_justification) FROM stdin;
951a449d-5f92-49c5-aec3-b3de06c44bcf	f	10	t	t	2026-06-15 14:52:40.780285	t	12.00	t	f	f	12.00	t	t
cf26f84d-f21f-4138-a024-e6ce33797ffd	f	10	t	t	2026-06-13 20:06:59.620715	f	2.00	t	t	f	12.00	t	t
bdd57572-5518-48c0-9e27-b9f2c23591de	f	10	t	t	2026-06-14 17:44:24.686912	f	2.00	t	t	f	12.00	t	t
cbbf551f-87c4-47f4-aa8b-cd20e7036a61	f	10	t	t	2026-06-18 07:43:57.339587	f	2.00	t	t	f	12.00	t	t
\.


--
-- Data for Name: incident_notes; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.incident_notes (id, incident_id, author_id, author_name, content, created_at) FROM stdin;
db663d85-b614-43b2-a466-f9393c98313a	63b49518-160f-4511-bf7f-7849cde38361	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	Info Jjac	Es una nota para probar	2026-06-08 11:32:10.245772
98707535-c191-43fd-9625-1efceef1b37f	63b49518-160f-4511-bf7f-7849cde38361	\N	Sistema	📱 WhatsApp enviado: Gracias! gestionado	2026-06-08 11:32:26.621652
7c3799b6-fd2d-4db9-9eb7-89e431a87cd6	c4939520-8f44-4a24-857e-9cff69ce629d	\N	Sistema	📱 WhatsApp enviado: ok, perfecto.\n📎 [Invoice-PTM7IOZ1-0001.pdf](/uploads/02177b37-4a90-45bc-baf7-a9ab279a4335_Invoice-PTM7IOZ1-0001.pdf)	2026-06-08 15:00:35.110284
a373672a-b289-4513-abfd-81b745b1cc12	de8122fa-1795-40fa-934a-6cd185987b03	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	Info Jjac	✏️ Fichaje modificado desde incidencia (07/06/2026 04:09)	2026-06-08 15:06:34.621876
4d37236d-84e1-48cd-be2b-60deae843d3c	63b49518-160f-4511-bf7f-7849cde38361	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	Info Jjac	✏️ Parada creada desde incidencia (inicio_parada, 08/06/2026 13:25)	2026-06-08 15:25:34.53198
029143bb-bf7c-4ed2-a8e3-eb6a7dff5aad	7831815a-c105-40b7-83a0-34ee7d053c02	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	rectificamos hora	2026-06-12 11:24:32.420132
21f6a9af-b4dd-44e5-ac28-ef2c731f5633	7831815a-c105-40b7-83a0-34ee7d053c02	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	✏️ Fichaje modificado desde incidencia (12/06/2026 07:30)	2026-06-12 11:24:45.636677
55f7f1da-9c71-40a8-a3cd-07f013703828	3cebfd5e-561c-4c9b-a3dc-acda306516dc	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	✏️ Fichaje modificado desde incidencia (15/06/2026 07:30)	2026-06-15 08:21:56.486407
59afe6c3-f62d-4e8c-a217-aff9554c9e2e	1fd3264f-9b8f-499a-be83-8229ac215762	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	✏️ Fichaje modificado desde incidencia (12/06/2026 07:30)	2026-06-15 08:34:23.938485
e0a53eee-fd60-4ea5-a1dc-01e0835ec0cd	40e6eb01-a1a1-44bc-8cc0-1f83e58138b9	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	✏️ Fichaje modificado desde panel: entrada: 15/06 05:29 → 15/06 07:29	2026-06-16 08:05:12.972418
2a92b206-c1e3-49d7-a632-f2f8e8702a83	26b339f0-70b2-4360-87d9-1ed606947fdb	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	✏️ Fichaje modificado desde incidencia (15/06/2026 07:30)	2026-06-16 08:08:52.908773
fbe999b2-a517-4c16-808a-db5a739c2413	3cebfd5e-561c-4c9b-a3dc-acda306516dc	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	✏️ Fichaje modificado desde panel: entrada: 15/06 07:30 → 15/06 05:30; salida: 16/06 12:05 → 15/06 10:05	2026-06-16 08:09:08.342593
e118b669-2be0-4dd8-a083-1c74d4b99341	26b339f0-70b2-4360-87d9-1ed606947fdb	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	✏️ Fichaje modificado desde incidencia (15/06/2026 07:30)	2026-06-17 07:35:47.072805
3380b636-2d6a-4fb9-b37b-84719a87df89	c8adf3b5-785b-4a29-a444-0c23a68e2cdc	c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	✏️ Fichaje modificado desde incidencia (17/06/2026 07:30)	2026-06-17 09:53:31.975631
\.


--
-- Data for Name: incidents; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.incidents (id, tenant_id, employee_id, category, incident_type, status, source, title, description, clock_in_id, leave_request_id, minutes_late, original_data, modified_data, employee_justification, internal_notes, public_token, whatsapp_notified_at, justified_at, resolved_at, resolved_by_id, created_at, updated_at, created_by_id, managed, break_id, incident_date) FROM stdin;
486fb2f1-6c94-4cab-a78e-a83a87186b1c	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	fichaje	manual	open	whatsapp	si, por favor	si, por favor	\N	\N	\N	{}	null	\N	\N	\N	\N	\N	\N	\N	2026-06-06 15:46:46.202237	2026-06-06 15:46:46.202268	\N	f	\N	\N
c4939520-8f44-4a24-857e-9cff69ce629d	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	fichaje	manual	resolved	panel	Modificación de fichaje: entrada: 08/06 11:21 → 08/06 09:21; salida: — → 08/06 14:00	\N	de30f012-8210-4dda-8a0d-db9893cbf910	\N	\N	{"entrada_at": "2026-06-08T11:21:24.142816+00:00", "salida_at": null, "notes": null, "project_id": "a145d4f4-3f15-4c23-93bc-51a09947a031"}	{"entrada_at": "2026-06-08T09:21:00+00:00", "salida_at": "2026-06-08T14:00:00+00:00", "notes": "Se ha confundido", "project_id": "a145d4f4-3f15-4c23-93bc-51a09947a031"}	\N	\N	\N	\N	\N	2026-06-08 14:00:03.801816	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	2026-06-08 14:00:03.796055	2026-06-08 15:00:35.114032	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	t	\N	2026-06-08
de8122fa-1795-40fa-934a-6cd185987b03	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	fichaje	manual	resolved	whatsapp	el viernes se me olvió fichar también 😑😑	\N	1546eb4d-2fe9-4d74-ad9a-e2c662453fac	\N	\N	{"entrada_at": "2026-06-07T06:09:36.852841+00:00", "salida_at": "2026-06-07T07:54:27.639188+00:00"}	{"entrada_at": "2026-06-07T04:09:00+00:00", "salida_at": "2026-06-07T13:50:00+00:00"}	\N	\N	\N	\N	\N	2026-06-08 11:33:37.06152	f41acab0-d7a1-4441-942b-69664ceb9d3b	2026-06-08 11:33:37.061672	2026-06-08 15:06:34.626633	f41acab0-d7a1-4441-942b-69664ceb9d3b	t	\N	\N
63b49518-160f-4511-bf7f-7849cde38361	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	fichaje	manual	resolved	whatsapp	si, por favor y abre la entrada	\N	\N	\N	\N	{}	null	\N	\N	\N	\N	\N	2026-06-08 11:18:42.905041	f41acab0-d7a1-4441-942b-69664ceb9d3b	2026-06-08 11:18:42.905258	2026-06-08 15:25:34.534245	f41acab0-d7a1-4441-942b-69664ceb9d3b	t	f091c69b-9ce3-4442-8cbd-b89868bb49a1	\N
40e6eb01-a1a1-44bc-8cc0-1f83e58138b9	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	fichaje	manual	resolved	panel	Modificación de fichaje: entrada: 15/06 07:29 → 15/06 05:29; salida: — → 15/06 12:00	\N	8d17021b-1d9e-45a7-b8a7-fdf4093f4b27	\N	\N	{"entrada_at": "2026-06-15T07:29:00+00:00", "salida_at": null, "notes": null, "project_id": null}	{"entrada_at": "2026-06-15T07:29:00+00:00", "salida_at": "2026-06-15T12:00:00+00:00", "notes": null, "project_id": null}	\N	\N	\N	\N	\N	2026-06-16 08:05:12.972143	c3136edf-351e-4329-8050-720ecd216410	2026-06-16 08:04:49.982553	2026-06-16 08:05:12.97653	c3136edf-351e-4329-8050-720ecd216410	t	\N	2026-06-15
1fd3264f-9b8f-499a-be83-8229ac215762	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	fichaje	manual	resolved	whatsapp	Cerrar fichaje del 12/06	Cerrar jornada del 2026-06-12 a las 14:00	b8e291fd-876f-4eeb-b4bb-75f0a8e9e48b	\N	\N	{"entrada_at": "2026-06-12T07:30:00+00:00", "salida_at": null}	{"entrada_at": "2026-06-12T07:30:00+00:00", "salida_at": "2026-06-12T12:02:00+00:00"}	\N	\N	\N	\N	\N	2026-06-15 08:33:22.63843	c3136edf-351e-4329-8050-720ecd216410	2026-06-15 08:33:22.638601	2026-06-15 08:34:23.942183	c3136edf-351e-4329-8050-720ecd216410	t	\N	2026-06-12
7831815a-c105-40b7-83a0-34ee7d053c02	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	fichaje	manual	resolved	whatsapp	Olvido fichaje entrada	Se me olvidó fichar la entrada hoy. Entré a las 09:30.	b8e291fd-876f-4eeb-b4bb-75f0a8e9e48b	\N	\N	{"entrada_at": "2026-06-12T11:22:06.075977+00:00", "salida_at": null}	{"entrada_at": "2026-06-12T07:30:00+00:00", "salida_at": null}	\N	\N	\N	\N	\N	2026-06-12 11:23:25.500574	c3136edf-351e-4329-8050-720ecd216410	2026-06-12 11:23:25.500928	2026-06-12 11:24:45.63991	c3136edf-351e-4329-8050-720ecd216410	t	\N	2026-06-12
0508407d-2e81-494a-9910-38a5059f2eb6	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	fichaje	manual	resolved	panel	Modificación de fichaje: salida: — → 15/06 07:29	\N	bd686ef3-0e6b-4e43-b725-3806cfae2ffd	\N	\N	{"entrada_at": "2026-06-15T07:29:00+00:00", "salida_at": null, "notes": null, "project_id": null}	{"entrada_at": "2026-06-15T07:29:00+00:00", "salida_at": "2026-06-15T07:29:00+00:00", "notes": null, "project_id": null}	\N	\N	\N	\N	\N	2026-06-15 08:37:19.246185	c3136edf-351e-4329-8050-720ecd216410	2026-06-15 08:37:19.24139	2026-06-15 08:37:19.241415	c3136edf-351e-4329-8050-720ecd216410	t	\N	2026-06-15
d3902b05-e40c-4c91-8ca2-4a044ec183bf	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	fichaje	missing_clock_in	open	auto	Sin entrada registrada (07:00)	No se ha registrado entrada. Horario previsto desde las 07:00.	\N	\N	\N	{"expected_start_time": "07:00:00"}	null	\N	\N	\N	\N	\N	\N	\N	2026-06-15 17:01:21.356579	2026-06-15 17:01:21.356596	\N	f	\N	2026-06-15
3b14262e-1e40-46eb-82e2-929239cba7e2	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	fichaje	manual	resolved	whatsapp	Cancelación de solicitud de vacaciones	Benito solicita cancelar sus vacaciones ya pedidas.	\N	\N	\N	{}	null	\N	\N	\N	\N	\N	2026-06-16 07:33:56.573349	f41acab0-d7a1-4441-942b-69664ceb9d3b	2026-06-16 07:33:56.573505	2026-06-16 07:33:56.573527	f41acab0-d7a1-4441-942b-69664ceb9d3b	f	\N	2026-06-16
4e499649-0c79-4226-8088-3f03067e2f48	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	fichaje	manual	resolved	panel	Modificación de fichaje: entrada: 18/06 07:35 → 18/06 07:30; salida: 18/06 15:45 → 18/06 15:30	\N	71c96dbe-2c68-4516-9484-a0cc9ed4c0a3	\N	\N	{"entrada_at": "2026-06-18T07:35:31.443241+00:00", "salida_at": "2026-06-18T15:45:49.357529+00:00", "notes": null, "project_id": null}	{"entrada_at": "2026-06-18T07:30:00+00:00", "salida_at": "2026-06-18T15:30:00+00:00", "notes": null, "project_id": null}	\N	\N	\N	\N	\N	2026-06-19 07:41:29.050628	c3136edf-351e-4329-8050-720ecd216410	2026-06-19 07:41:29.048678	2026-06-19 07:41:29.048694	c3136edf-351e-4329-8050-720ecd216410	t	\N	2026-06-18
d9a0224c-d8c9-47bd-8dcc-ec9fcc8ce930	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	fichaje	manual	resolved	panel	Modificación de fichaje: entrada: 16/06 08:07 → 16/06 07:28	\N	aec60e3c-e25a-4177-93ba-48bf592ec9f1	\N	\N	{"entrada_at": "2026-06-16T08:07:17.798856+00:00", "salida_at": null, "notes": null, "project_id": null}	{"entrada_at": "2026-06-16T07:28:00+00:00", "salida_at": null, "notes": null, "project_id": null}	\N	\N	\N	\N	\N	2026-06-16 08:13:54.257445	c3136edf-351e-4329-8050-720ecd216410	2026-06-16 08:13:54.255627	2026-06-16 08:13:54.255644	c3136edf-351e-4329-8050-720ecd216410	t	\N	2026-06-16
3cebfd5e-561c-4c9b-a3dc-acda306516dc	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	fichaje	manual	resolved	whatsapp	Corrección hora entrada	El empleado entró a las 9:30 pero fichó a las 9:47. Solicita corregir la entrada a las 9:30 del 15/06/2026.	060a3f6b-7345-4b67-bb78-ca1248843980	\N	\N	{"entrada_at": "2026-06-15T07:47:34.942231+00:00", "salida_at": null}	{"entrada_at": "2026-06-15T05:30:00+00:00", "salida_at": "2026-06-15T10:05:00+00:00", "notes": null, "project_id": null}	\N	\N	\N	\N	\N	2026-06-16 08:09:08.342301	c3136edf-351e-4329-8050-720ecd216410	2026-06-15 08:18:58.582652	2026-06-16 08:09:08.345893	e5e24f2f-86ec-4321-8853-e394a494630e	t	\N	2026-06-15
c8adf3b5-785b-4a29-a444-0c23a68e2cdc	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	fichaje	manual	resolved	whatsapp	Olvido de fichaje	Se me ha olvidado fichar a las 9:30 del 17/06/2026	191f0da0-1e83-44b2-b9c8-ea5eabd701f8	\N	\N	{"entrada_at": "2026-06-17T09:52:29.685669+00:00", "salida_at": null}	{"entrada_at": "2026-06-17T07:30:00+00:00", "salida_at": null}	\N	\N	\N	\N	\N	2026-06-17 09:53:16.741621	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	2026-06-17 09:53:16.741755	2026-06-17 09:53:31.983135	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	t	\N	2026-06-17
421eaf9a-e84c-40f3-acd4-4d8c3c77cd04	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	fichaje	missing_clock_in	open	auto	Sin entrada registrada (09:00)	No se ha registrado entrada. Horario previsto desde las 09:00.	\N	\N	\N	{"expected_start_time": "09:00:00"}	null	\N	\N	\N	\N	\N	\N	\N	2026-06-18 19:00:20.503746	2026-06-18 19:00:20.503778	\N	f	\N	2026-06-18
26b339f0-70b2-4360-87d9-1ed606947fdb	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	fichaje	manual	resolved	whatsapp	Corrección salida 15/06/2026	Corregir la salida del 15/06/2026 a las 14:00	060a3f6b-7345-4b67-bb78-ca1248843980	\N	\N	{"entrada_at": "2026-06-15T07:30:00+00:00", "salida_at": "2026-06-16T08:05:15.696933+00:00"}	{"entrada_at": "2026-06-15T07:30:00+00:00", "salida_at": "2026-06-15T12:05:00+00:00"}	\N	\N	\N	\N	\N	2026-06-16 08:05:59.043696	e5e24f2f-86ec-4321-8853-e394a494630e	2026-06-16 08:05:59.043935	2026-06-17 07:35:47.07854	e5e24f2f-86ec-4321-8853-e394a494630e	t	\N	2026-06-15
afca92ec-8c8a-4459-a7e9-9c180a4f7889	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	fichaje	manual	resolved	panel	Modificación de fichaje: entrada: 18/06 15:45 → 18/06 15:31; salida: 19/06 07:40 → 18/06 15:32	\N	a6b8bde4-b5de-4e1a-9f92-66ac034274cc	\N	\N	{"entrada_at": "2026-06-18T15:45:59.369611+00:00", "salida_at": "2026-06-19T07:40:09.423373+00:00", "notes": null, "project_id": null}	{"entrada_at": "2026-06-18T15:31:00+00:00", "salida_at": "2026-06-18T15:32:00+00:00", "notes": null, "project_id": null}	\N	\N	\N	\N	\N	2026-06-19 07:42:00.083081	c3136edf-351e-4329-8050-720ecd216410	2026-06-19 07:42:00.081442	2026-06-19 07:42:00.081477	c3136edf-351e-4329-8050-720ecd216410	t	\N	2026-06-18
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.invoices (id, tenant_id, number, recipient_legal_name, recipient_tax_id, recipient_address, recipient_city, recipient_postal_code, recipient_province, recipient_country, recipient_email, concept, base_cents, vat_rate, vat_cents, total_cents, currency, issue_date, due_date, status, stripe_payment_id, credit_note_for_id, pdf_url, email_sent_at, created_at, updated_at, ls_payment_id) FROM stdin;
0e066823-b28b-4d6e-a554-fe194ab88560	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	ALC-2026-0004	prueba liaño 2	B90000093	\N	\N	\N	\N	ES	lblr81@gmail.com	Suscripción Lemon Squeezy	4959	21	1041	6000	EUR	2026-06-14	\N	PAID	\N	\N	/uploads/invoices/ALC-2026-0004.pdf	2026-06-14 17:46:47.293006	2026-06-14 17:46:46.31407	2026-06-14 17:46:46.314107	f88d9d84-671b-4bcd-a39c-7c0a11021b6f
\.


--
-- Data for Name: leave_requests; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.leave_requests (id, employee_id, start_date, end_date, days_requested, status, reason, supervisor_id, reviewed_at, review_notes, created_at, raw_message, leave_type_id) FROM stdin;
fe0a7d95-fee4-4d81-b15e-bf18e574043b	f41acab0-d7a1-4441-942b-69664ceb9d3b	2026-06-08	2026-06-08	1	PENDING	médico	\N	\N	\N	2026-06-06 18:54:27.808944	si, por favor	\N
67568cdc-2ae7-484e-8f8b-2ed0094a8e0f	f41acab0-d7a1-4441-942b-69664ceb9d3b	2026-06-15	2026-06-16	2	APPROVED	si	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	\N		2026-06-07 08:24:02.391321	si	325ecbf1-c3e2-489d-8afa-90bc7a36c636
0901284d-b6aa-4519-b87d-21e436da993d	f41acab0-d7a1-4441-942b-69664ceb9d3b	2026-06-12	2026-06-12	1	APPROVED	acompañar a mi hija al médico	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	\N		2026-06-08 16:42:34.372515	si	0191702b-713b-4bd9-9a1b-134a642d86fa
580d739e-d6ea-4627-bea6-01203aa49148	c3136edf-351e-4329-8050-720ecd216410	2026-06-16	2026-06-17	2	APPROVED	Días acumulados solicitados	e5e24f2f-86ec-4321-8853-e394a494630e	\N		2026-06-12 11:27:10.420257	si	0a6ffda0-682a-43d3-ba5a-146d7c4a93f6
2e34891f-a1fc-4a74-8c29-da3a7447bc52	f41acab0-d7a1-4441-942b-69664ceb9d3b	2026-06-17	2026-06-19	3	PENDING	\N	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	\N	\N	2026-06-16 05:44:31.664341	Si	3ef23398-fffe-40a1-80d8-cf188f3b3584
1d621424-1167-4c17-b9c3-acc5c5a89535	f41acab0-d7a1-4441-942b-69664ceb9d3b	2026-07-01	2026-07-15	11	PENDING	\N	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	\N	\N	2026-06-16 08:13:42.095741	si	3ef23398-fffe-40a1-80d8-cf188f3b3584
8523fb84-b883-4d7a-a68d-90cf71b58e30	e5e24f2f-86ec-4321-8853-e394a494630e	2026-06-19	2026-06-19	1	PENDING	\N	\N	\N	\N	2026-06-19 07:23:04.402982	Si	a16dcf33-30f2-4dab-9cfb-c02b00e97a71
\.


--
-- Data for Name: leave_types; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.leave_types (id, tenant_id, name, deducts_balance, is_default, is_active, sort_order, created_at, has_own_balance, default_days) FROM stdin;
8817800b-595c-4eeb-9654-97485c8e239c	cf26f84d-f21f-4138-a024-e6ce33797ffd	Vacaciones	t	t	t	0	2026-06-06 22:21:59.846789	f	\N
c81e7fd0-2b5f-45f5-ad98-2af1d6bbcfbf	cf26f84d-f21f-4138-a024-e6ce33797ffd	Baja	f	t	t	1	2026-06-06 22:21:59.846789	f	\N
3ef23398-fffe-40a1-80d8-cf188f3b3584	951a449d-5f92-49c5-aec3-b3de06c44bcf	Vacaciones	t	t	t	0	2026-06-06 22:21:59.846789	f	\N
0191702b-713b-4bd9-9a1b-134a642d86fa	951a449d-5f92-49c5-aec3-b3de06c44bcf	Baja	f	t	t	1	2026-06-06 22:21:59.846789	f	\N
325ecbf1-c3e2-489d-8afa-90bc7a36c636	951a449d-5f92-49c5-aec3-b3de06c44bcf	Dias acumulados	f	f	t	0	2026-06-07 08:04:36.582147	t	0
a16dcf33-30f2-4dab-9cfb-c02b00e97a71	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	Vacaciones	t	t	t	0	2026-06-07 17:16:11.774732	f	\N
f6da0748-0e59-455b-a382-d8661d075dbd	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	Baja	f	t	t	1	2026-06-07 17:16:11.774732	f	\N
0a6ffda0-682a-43d3-ba5a-146d7c4a93f6	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	Dias acumulados	f	f	t	0	2026-06-12 11:13:21.412163	t	0
d36e7180-d8a2-4831-ac98-4b19fa8015ba	bdd57572-5518-48c0-9e27-b9f2c23591de	Vacaciones	t	t	t	0	2026-06-14 17:42:41.221544	f	\N
b4f27e95-b94d-431a-b248-122af8a19743	bdd57572-5518-48c0-9e27-b9f2c23591de	Baja	f	t	t	1	2026-06-14 17:42:41.221544	f	\N
70de4462-f26c-4513-beca-f185b60b2141	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	Vacaciones	t	t	t	0	2026-06-14 17:53:19.251119	f	\N
6ead2580-a461-404d-b4f3-07aab6da8890	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	Baja	f	t	t	1	2026-06-14 17:53:19.251119	f	\N
\.


--
-- Data for Name: legal_acceptances; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.legal_acceptances (id, employee_id, legal_document_id, document_version, accepted_at, channel) FROM stdin;
3dc2faf3-fcd4-4f07-8c07-1957ffdfca58	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	5c5906bc-7071-495a-884a-25574eee4ace	1	2026-06-05 06:44:53.738054	web
c158fbc5-f440-480d-81f6-11201a4342ec	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	6c76fdc4-4b6f-4501-9f11-8d8c5bae3d96	1	2026-06-05 06:44:55.536504	web
9059d50d-9c07-45fa-bda5-a28d0157e52f	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	2c9c084f-eee1-4015-9b76-5e48840880bc	1	2026-06-05 06:44:56.735822	web
e83c0acd-9e7e-4bba-a6df-056ace610db4	f41acab0-d7a1-4441-942b-69664ceb9d3b	5c5906bc-7071-495a-884a-25574eee4ace	1	2026-06-07 10:04:17.627388	whatsapp
f85a9ed6-4004-44a2-a2aa-0bc096cc99a4	f41acab0-d7a1-4441-942b-69664ceb9d3b	6c76fdc4-4b6f-4501-9f11-8d8c5bae3d96	1	2026-06-07 10:04:19.728297	whatsapp
b16bcd7a-79c7-4854-8591-5d69aeb3877d	f41acab0-d7a1-4441-942b-69664ceb9d3b	2c9c084f-eee1-4015-9b76-5e48840880bc	1	2026-06-07 10:04:21.025136	whatsapp
ec7160ba-1c19-49a5-8530-1fbce7bfd952	941a5698-80fc-41ec-87c7-1fe4fa28ba75	a84544b9-f03e-4ddd-bf4f-eb48111e08be	1	2026-06-07 16:57:19.905105	web
b8c4bd8e-64dd-4685-a7a5-af04175bc8f5	941a5698-80fc-41ec-87c7-1fe4fa28ba75	2a214236-b402-452e-9d1a-e8aa01a371de	1	2026-06-07 16:57:20.973414	web
c4337aaa-32e9-456d-822c-84daff37dace	941a5698-80fc-41ec-87c7-1fe4fa28ba75	2bca9d22-79e8-4c7a-89f0-30922f348826	1	2026-06-07 16:57:22.271645	web
0431fd9b-9e22-4046-995b-da62d4454628	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	5c5906bc-7071-495a-884a-25574eee4ace	1	2026-06-11 03:57:41.481673	whatsapp
c19491e7-e4af-4ab5-837a-b7d3294966a6	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	6c76fdc4-4b6f-4501-9f11-8d8c5bae3d96	1	2026-06-11 03:57:43.19593	whatsapp
187afc6e-9e96-4d1f-8b00-58468d1f529f	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	2c9c084f-eee1-4015-9b76-5e48840880bc	1	2026-06-11 03:57:44.119254	whatsapp
750615ea-b5fe-44dd-bbbc-176425ec7ee2	c3136edf-351e-4329-8050-720ecd216410	a84544b9-f03e-4ddd-bf4f-eb48111e08be	1	2026-06-12 11:08:49.302141	web
a05203e7-b30d-45b6-9a66-924538056fcd	c3136edf-351e-4329-8050-720ecd216410	2a214236-b402-452e-9d1a-e8aa01a371de	1	2026-06-12 11:08:51.691334	web
38ce08ad-8a58-40fa-a632-b63bc6355bae	c3136edf-351e-4329-8050-720ecd216410	2bca9d22-79e8-4c7a-89f0-30922f348826	1	2026-06-12 11:08:53.732933	web
59baff31-9e16-494b-9bc5-510eb9a3e278	e5e24f2f-86ec-4321-8853-e394a494630e	a84544b9-f03e-4ddd-bf4f-eb48111e08be	1	2026-06-12 11:29:58.053568	whatsapp
69247d91-1b9b-411f-854e-533446cd47e0	e5e24f2f-86ec-4321-8853-e394a494630e	2a214236-b402-452e-9d1a-e8aa01a371de	1	2026-06-12 11:29:59.576006	whatsapp
3905fa1f-e969-4219-8dbc-a26432f79c88	e5e24f2f-86ec-4321-8853-e394a494630e	2bca9d22-79e8-4c7a-89f0-30922f348826	1	2026-06-12 11:30:01.717114	whatsapp
2bfe793b-7e07-4641-b33e-52c790985bf8	c9e697a9-48eb-4f8d-a9ba-d9b1be9ccbd9	80427f65-acb9-4913-bef0-4633ff1b6595	1	2026-06-14 17:50:11.146863	web
6f49de9f-7b80-4273-a55a-33c73d645737	c9e697a9-48eb-4f8d-a9ba-d9b1be9ccbd9	adec9b8a-3e10-40d2-844c-3aea3d6ffb35	1	2026-06-14 17:50:12.337	web
5d8afd5c-41e5-4ff1-b31f-4dc941cb4b51	c9e697a9-48eb-4f8d-a9ba-d9b1be9ccbd9	25f0d91d-8db6-4c19-8330-5b301a8b99d6	1	2026-06-14 17:50:13.78087	web
a9566281-4242-44e2-aa94-93873a9679db	2e344a27-169d-44fa-8151-0e643749dc33	a84544b9-f03e-4ddd-bf4f-eb48111e08be	1	2026-06-17 07:11:01.668404	whatsapp
2cc8086c-7e7b-4ffc-87a9-6bbfabf5e76b	2e344a27-169d-44fa-8151-0e643749dc33	2a214236-b402-452e-9d1a-e8aa01a371de	1	2026-06-17 07:11:06.548798	whatsapp
269106ea-0977-4cc2-985c-693dd7041f08	2e344a27-169d-44fa-8151-0e643749dc33	2bca9d22-79e8-4c7a-89f0-30922f348826	1	2026-06-17 07:11:11.388487	whatsapp
731371b6-9886-407d-ae6d-c450b6865435	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	a84544b9-f03e-4ddd-bf4f-eb48111e08be	1	2026-06-17 09:50:59.873779	whatsapp
5a914696-ba49-4bae-bcba-c1ede199bb85	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	2a214236-b402-452e-9d1a-e8aa01a371de	1	2026-06-17 09:51:01.074104	whatsapp
e4d18c18-a48d-4140-9c83-2fc0329aedc0	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	2bca9d22-79e8-4c7a-89f0-30922f348826	1	2026-06-17 09:51:01.71058	whatsapp
\.


--
-- Data for Name: legal_documents; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.legal_documents (id, tenant_id, code, title, body, version, is_active, is_required, sort_order, created_at, updated_at) FROM stdin;
d7cabdb3-14da-4fe4-b21f-219d8f721aa5	cf26f84d-f21f-4138-a024-e6ce33797ffd	time_tracking	Registro de jornada laboral	Declaro haber sido informado/a de la obligación de registrar la jornada laboral conforme al Real Decreto-ley 8/2019 y al reglamento interno de la empresa. Autorizo el tratamiento de mis datos de fichaje para fines laborales y de cumplimiento legal.	1	t	t	0	2026-05-25 18:50:56.029329	2026-05-25 18:50:56.029351
7313c3ef-d09c-4272-88cc-30bd898dc93d	cf26f84d-f21f-4138-a024-e6ce33797ffd	privacy	Política de privacidad y protección de datos	He leído y acepto la política de privacidad y el tratamiento de mis datos personales conforme al RGPD y la LOPDGDD, para la gestión de la relación laboral, nóminas, comunicaciones y servicios de recursos humanos.	1	t	t	1	2026-05-25 18:50:56.033268	2026-05-25 18:50:56.033285
a0f9d6b9-37b6-4483-a271-c8e1d2f4755b	cf26f84d-f21f-4138-a024-e6ce33797ffd	internal_rules	Normativa interna y uso de medios digitales	Acepto conocer y cumplir la normativa interna de la empresa, incluido el uso responsable de herramientas digitales, WhatsApp corporativo para fichajes cuando aplique, y las políticas de seguridad de la información.	1	t	t	2	2026-05-25 18:50:56.034835	2026-05-25 18:50:56.03485
5c5906bc-7071-495a-884a-25574eee4ace	951a449d-5f92-49c5-aec3-b3de06c44bcf	time_tracking	Registro de jornada laboral	Declaro haber sido informado/a de la obligación de registrar la jornada laboral conforme al Real Decreto-ley 8/2019 y al reglamento interno de la empresa. Autorizo el tratamiento de mis datos de fichaje para fines laborales y de cumplimiento legal.	1	t	t	0	2026-05-25 20:02:55.932444	2026-05-25 20:02:55.932459
6c76fdc4-4b6f-4501-9f11-8d8c5bae3d96	951a449d-5f92-49c5-aec3-b3de06c44bcf	privacy	Política de privacidad y protección de datos	He leído y acepto la política de privacidad y el tratamiento de mis datos personales conforme al RGPD y la LOPDGDD, para la gestión de la relación laboral, nóminas, comunicaciones y servicios de recursos humanos.	1	t	t	1	2026-05-25 20:02:55.93509	2026-05-25 20:02:55.935105
2c9c084f-eee1-4015-9b76-5e48840880bc	951a449d-5f92-49c5-aec3-b3de06c44bcf	internal_rules	Normativa interna y uso de medios digitales	Acepto conocer y cumplir la normativa interna de la empresa, incluido el uso responsable de herramientas digitales, WhatsApp corporativo para fichajes cuando aplique, y las políticas de seguridad de la información.	1	t	t	2	2026-05-25 20:02:55.936516	2026-05-25 20:02:55.936531
a84544b9-f03e-4ddd-bf4f-eb48111e08be	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	time_tracking	Registro de jornada laboral	Declaro haber sido informado/a de la obligación de registrar la jornada laboral conforme al Real Decreto-ley 8/2019 y al reglamento interno de la empresa. Autorizo el tratamiento de mis datos de fichaje para fines laborales y de cumplimiento legal.	1	t	t	0	2026-06-07 16:55:41.58735	2026-06-07 16:55:41.587367
2a214236-b402-452e-9d1a-e8aa01a371de	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	privacy	Política de privacidad y protección de datos	He leído y acepto la política de privacidad y el tratamiento de mis datos personales conforme al RGPD y la LOPDGDD, para la gestión de la relación laboral, nóminas, comunicaciones y servicios de recursos humanos.	1	t	t	1	2026-06-07 16:55:41.589927	2026-06-07 16:55:41.589942
2bca9d22-79e8-4c7a-89f0-30922f348826	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	internal_rules	Normativa interna y uso de medios digitales	Acepto conocer y cumplir la normativa interna de la empresa, incluido el uso responsable de herramientas digitales, WhatsApp corporativo para fichajes cuando aplique, y las políticas de seguridad de la información.	1	t	t	2	2026-06-07 16:55:41.591384	2026-06-07 16:55:41.591399
8703fdef-fd02-45a0-981b-5733ebeed28e	bdd57572-5518-48c0-9e27-b9f2c23591de	time_tracking	Registro de jornada laboral	Declaro haber sido informado/a de la obligación de registrar la jornada laboral conforme al Real Decreto-ley 8/2019 y al reglamento interno de la empresa. Autorizo el tratamiento de mis datos de fichaje para fines laborales y de cumplimiento legal.	1	t	t	0	2026-06-14 17:37:01.265069	2026-06-14 17:37:01.265085
2a924c28-b550-449c-87fb-c8095244772b	bdd57572-5518-48c0-9e27-b9f2c23591de	privacy	Política de privacidad y protección de datos	He leído y acepto la política de privacidad y el tratamiento de mis datos personales conforme al RGPD y la LOPDGDD, para la gestión de la relación laboral, nóminas, comunicaciones y servicios de recursos humanos.	1	t	t	1	2026-06-14 17:37:01.269748	2026-06-14 17:37:01.269763
ef64b62c-786e-47c2-925b-b119c7567744	bdd57572-5518-48c0-9e27-b9f2c23591de	internal_rules	Normativa interna y uso de medios digitales	Acepto conocer y cumplir la normativa interna de la empresa, incluido el uso responsable de herramientas digitales, WhatsApp corporativo para fichajes cuando aplique, y las políticas de seguridad de la información.	1	t	t	2	2026-06-14 17:37:01.271364	2026-06-14 17:37:01.27138
80427f65-acb9-4913-bef0-4633ff1b6595	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	time_tracking	Registro de jornada laboral	Declaro haber sido informado/a de la obligación de registrar la jornada laboral conforme al Real Decreto-ley 8/2019 y al reglamento interno de la empresa. Autorizo el tratamiento de mis datos de fichaje para fines laborales y de cumplimiento legal.	1	t	t	0	2026-06-14 17:45:13.477262	2026-06-14 17:45:13.47728
adec9b8a-3e10-40d2-844c-3aea3d6ffb35	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	privacy	Política de privacidad y protección de datos	He leído y acepto la política de privacidad y el tratamiento de mis datos personales conforme al RGPD y la LOPDGDD, para la gestión de la relación laboral, nóminas, comunicaciones y servicios de recursos humanos.	1	t	t	1	2026-06-14 17:45:13.479622	2026-06-14 17:45:13.479637
25f0d91d-8db6-4c19-8330-5b301a8b99d6	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	internal_rules	Normativa interna y uso de medios digitales	Acepto conocer y cumplir la normativa interna de la empresa, incluido el uso responsable de herramientas digitales, WhatsApp corporativo para fichajes cuando aplique, y las políticas de seguridad de la información.	1	t	t	2	2026-06-14 17:45:13.48106	2026-06-14 17:45:13.481075
\.


--
-- Data for Name: legal_tokens; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.legal_tokens (id, token, employee_id, tenant_id, expires_at, used_at, created_at) FROM stdin;
839adab2-4298-4943-a19a-29ac811d35e5	zQB3kCy5ff1LresTY1MG1_FdJfO1jhVO0O7IchIrn-g	f41acab0-d7a1-4441-942b-69664ceb9d3b	951a449d-5f92-49c5-aec3-b3de06c44bcf	2026-06-07 10:09:03.535193	2026-06-07 10:04:21.037524	2026-06-07 10:04:03.53546
f48bb751-5c18-4e91-90bf-017bb4a06e7e	aBDUCdr7wLauPVE7LCZqgUP7o0FnnRmfJxcpUSM3lls	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	951a449d-5f92-49c5-aec3-b3de06c44bcf	2026-06-11 04:02:09.819106	2026-06-11 03:57:44.126634	2026-06-11 03:57:09.819347
aef23b24-92dc-4800-ac75-3187f6acd3f0	LFjiOihNHiijJWKjXGm4yCGRcfIEEA6JaVB7HEsdCSY	e5e24f2f-86ec-4321-8853-e394a494630e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	2026-06-12 11:34:34.077006	2026-06-12 11:30:01.732526	2026-06-12 11:29:34.077182
393cbfc0-35ff-4e67-8e56-637dc467ef25	39dti2Xuhturuz4JhUPh6Z75VR-zVQvWNgOft9F2xG4	a1111fc5-3fc9-44fb-b346-d5e39282b83d	cf26f84d-f21f-4138-a024-e6ce33797ffd	2026-06-12 18:17:57.108627	\N	2026-06-12 18:12:57.108886
03aad7b9-7de8-4149-a56e-3df48bdc1e19	FdAoRlMQf8TsDG-vcQyap5J9dfKyVsTaDj6iERVW9_8	2e344a27-169d-44fa-8151-0e643749dc33	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	2026-06-17 07:15:25.33933	2026-06-17 07:11:11.395656	2026-06-17 07:10:25.339533
92d8a94f-2bab-4f9d-9a45-64c1a372de7e	z_nZIgz8V2VfccBdrrveM1V61BaxeFx97YOcMajtL84	6d589c7c-ae6c-4c38-8b2c-7fc326fb0185	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	2026-06-17 09:55:48.104829	2026-06-17 09:51:01.719991	2026-06-17 09:50:48.105095
\.


--
-- Data for Name: ls_payments; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.ls_payments (id, tenant_id, subscription_id, ls_order_id, ls_subscription_id, ls_invoice_id, amount_cents, currency, status, description, invoice_number, receipt_url, paid_at, created_at) FROM stdin;
f88d9d84-671b-4bcd-a39c-7c0a11021b6f	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	9865ec57-73f4-420e-ab92-b35c33a8613e	\N	\N	7611077	6000	EUR	PAID	Suscripción Lemon Squeezy	\N	https://app.lemonsqueezy.com/my-orders/390a58a8-fb92-4407-842b-32efa6b3bb38/subscription-invoice/7611077?expires=1781480804&signature=56160e611c152554e177adc360c7f66edbd3195c0c39f5ea741a0fd83bfee5d0	2026-06-14 17:46:44.851296	2026-06-14 17:46:44.851464
\.


--
-- Data for Name: mail_logs; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.mail_logs (id, to_address, subject, event_type, success, detail, tenant_id, envelope_id, created_at) FROM stdin;
bf501bc4-e4bc-4600-81bc-ab19abc00a5a	beni4041@gmail.com	Prueba SMTP — alcurro	test	t	\N	\N	\N	2026-06-08 11:44:21.008367
3752467f-6ee9-416d-b67d-d2cf6467ca6a	beni4041@gmail.com	Prueba SMTP — alcurro	test	t	\N	\N	\N	2026-06-08 11:44:22.564014
85cccc53-9465-4a7b-ae09-3f1f289af204	beni4041@gmail.com	Firma de documento — FRM-20260608-160419	firma_solicitud	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	87708f6e-9fe6-4091-a034-021d40f3a32e	2026-06-08 16:04:20.833428
896dd619-70dc-4170-9140-87dcefee5031	lblr81@gmail.com	Firma de documento — FRM-20260608-160419	firma_solicitud	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	87708f6e-9fe6-4091-a034-021d40f3a32e	2026-06-08 16:04:22.441962
0d331b0e-a6ae-4c0e-8422-db61ed9e44aa	lblr81@gmail.com	Firma de documento — FRM-20260608-160419	firma_solicitud	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	87708f6e-9fe6-4091-a034-021d40f3a32e	2026-06-08 16:04:48.725006
c0a173be-252b-4107-9440-f9a557cf14bf	beni4041@gmail.com	Código de firma — FRM-20260608-160419	firma_otp	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	87708f6e-9fe6-4091-a034-021d40f3a32e	2026-06-08 16:05:37.009809
d60caec1-fa20-48bd-9184-81c6cc0e341f	lblr81@gmail.com	Firma de documento — FRM-20260608-160708	firma_solicitud	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	2026-06-08 16:07:10.121616
a979346a-e894-4ddc-b416-c6be360212cb	beni4041@gmail.com	Firma de documento — FRM-20260608-160708	firma_solicitud	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	2026-06-08 16:07:11.892443
db13606d-ef4a-4cf4-b480-9e89aa98c4b6	beni4041@gmail.com	Código de firma — FRM-20260608-160708	firma_otp	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	2026-06-08 16:07:33.47073
aee10291-328a-4112-9eb3-369e39f9ae33	lblr81@gmail.com	Código de firma — FRM-20260608-160708	firma_otp	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	2026-06-08 16:07:48.170218
0eb35133-9e4a-4342-9c1f-6ef6bc48e5e7	lblr81@gmail.com	Código de firma — FRM-20260608-160708	firma_otp	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	2026-06-08 16:09:04.189068
04d9640f-9a98-4b39-b5dd-00cc7626eb7a	info@jjac.es	Nueva solicitud de permiso [Baja] — Benito	leave_request	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	2026-06-08 16:42:35.274315
e8fe1ba5-d058-41c3-84ca-03e72370fca7	admin@jjac.es	Nueva solicitud de permiso [Baja] — Benito	leave_request	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	2026-06-08 16:42:36.176869
0e23f4a9-1552-4891-93b9-7af7c6f62266	beni4041@gmail.com	Solicitud de permiso [Baja] aprobada — 2026-06-12 al 2026-06-12	leave_request	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	2026-06-08 17:16:41.901866
60d1c9af-649b-48a1-8b20-65fba6b949ec	cdocobo@gmail.com	Nueva solicitud de permiso [Dias acumulados] — María Diaz Garrón	leave_request	t	\N	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	\N	2026-06-12 11:27:11.314538
28519e23-34d4-4241-8843-f4c0216d6eca	benito.barrios@dealerbest.com	Nueva solicitud de permiso [Dias acumulados] — María Diaz Garrón	leave_request	t	\N	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	\N	2026-06-12 11:27:12.230403
2a3304bb-fcd8-449b-96e0-75f081f85cd1	mdgarron@gmail.com	Solicitud de permiso [Dias acumulados] aprobada — 2026-06-16 al 2026-06-16	leave_request	t	\N	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	\N	2026-06-12 11:27:49.770802
abda4d53-c729-4bfe-bedc-4b65414b74bd	benito.barrios@dealerbest.com	Recuperación de contraseña — Puerta Sevilla	password_reset	t	\N	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	\N	2026-06-12 16:16:18.785062
88755272-004e-4bb3-911e-3ca2c6a1cd70	lblr81@gmail.com	Pago confirmado — alcurro (60.00 EUR)	invoice	t	\N	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	\N	2026-06-14 17:46:45.731647
2eb53e6f-585c-49d3-af0d-4584d458e6c3	lblr81@gmail.com	Pago confirmado — alcurro (60.00 EUR)	invoice	t	\N	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	\N	2026-06-14 17:46:48.169051
b9f4f346-10e9-4aef-bda4-c2484f491db4	info@jjac.es	Nueva solicitud de permiso [Vacaciones] — Benito	leave_request	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	2026-06-16 05:44:32.588992
265b5483-32d6-4e53-895b-45a68855e10e	admin@jjac.es	Nueva solicitud de permiso [Vacaciones] — Benito	leave_request	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	2026-06-16 05:44:33.520367
2a5bc269-d647-41b6-8f9f-e71175ffec9c	info@jjac.es	Nueva solicitud de permiso [Vacaciones] — Benito	leave_request	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	2026-06-16 08:13:43.044835
1af81a3c-1f45-4d0d-b994-86b29687978a	admin@jjac.es	Nueva solicitud de permiso [Vacaciones] — Benito	leave_request	t	\N	951a449d-5f92-49c5-aec3-b3de06c44bcf	\N	2026-06-16 08:13:43.945312
fd2b62ab-ae99-402d-9cdf-4ec463e5ef57	benito.barrios@dealerbest.com	Nueva solicitud de permiso [Vacaciones] — Carmen Docobo	leave_request	t	\N	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	\N	2026-06-19 07:23:05.358875
\.


--
-- Data for Name: notification_preferences; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.notification_preferences (id, employee_id, event_type, channel, enabled) FROM stdin;
f63b372f-842a-4064-92fa-ae278e49c7a4	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	inapp	t
7d134904-abeb-49a1-be99-93c507630ec9	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	inapp	t
2a7f8278-7a7e-4489-9123-905cd5a9ffc6	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	leave_request	inapp	t
455288c3-4397-464a-a5d4-72a4575a9a0a	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	leave_request	whatsapp	t
d51a658e-345f-43f1-8222-ded2ee746c5a	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	incident	inapp	t
7f8e8590-8ea5-4f46-9bd3-3bc750d022a7	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	incident	whatsapp	t
17156521-ed78-4c6f-98a5-cfea7ecf0031	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	document	inapp	t
b08d9263-066b-4af9-9d37-202d937740af	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	document	whatsapp	t
45bf873d-8691-42fd-88e4-3f9de45c0967	ef3409d9-798e-468c-9934-0b80e1ff7dc2	clock_in	inapp	t
912b57f0-d951-458a-a2fc-aa53c2c00679	ef3409d9-798e-468c-9934-0b80e1ff7dc2	clock_in	whatsapp	t
289017f0-ea6a-4eb6-a101-03a6d50d9d7f	ef3409d9-798e-468c-9934-0b80e1ff7dc2	clock_in	email	t
536563d0-d1e9-4953-a67d-9b28899f99dd	ef3409d9-798e-468c-9934-0b80e1ff7dc2	clock_out	inapp	t
56be8a8c-1eee-4a30-ba0c-09a5cf3bd7c0	ef3409d9-798e-468c-9934-0b80e1ff7dc2	clock_out	whatsapp	t
018842d6-aa2a-4b2d-931c-0f333023465e	ef3409d9-798e-468c-9934-0b80e1ff7dc2	clock_out	email	t
0fa6d468-17ac-4138-9489-fe9b5254edde	ef3409d9-798e-468c-9934-0b80e1ff7dc2	leave_request	inapp	t
21c2f40f-7882-4af3-a936-9a66dfb9cd2a	ef3409d9-798e-468c-9934-0b80e1ff7dc2	leave_request	whatsapp	t
38d158ee-2a56-414f-9118-7d6a523bdee5	ef3409d9-798e-468c-9934-0b80e1ff7dc2	leave_request	email	t
7b930774-fbdc-4810-bf43-c688cf388f66	ef3409d9-798e-468c-9934-0b80e1ff7dc2	incident	inapp	t
8fc9d2a3-748c-4c3b-88e2-c7f16babc534	ef3409d9-798e-468c-9934-0b80e1ff7dc2	incident	whatsapp	t
805a1808-e555-4787-b327-df67c9401ee9	ef3409d9-798e-468c-9934-0b80e1ff7dc2	incident	email	t
9f29ba93-f25e-456a-850d-a801d7a4c6cf	ef3409d9-798e-468c-9934-0b80e1ff7dc2	document	inapp	t
4bd01851-03a2-4e95-ab63-81282551b9f5	ef3409d9-798e-468c-9934-0b80e1ff7dc2	document	whatsapp	t
6a270670-61d6-4e74-b932-cf6a8b2e0828	ef3409d9-798e-468c-9934-0b80e1ff7dc2	document	email	t
7c7755b5-25d2-41e9-8f96-2b5bc4a83eb0	f41acab0-d7a1-4441-942b-69664ceb9d3b	clock_in	inapp	t
128d7f70-f9c7-448c-b08d-9ec7c75bdba7	f41acab0-d7a1-4441-942b-69664ceb9d3b	clock_in	whatsapp	t
f18d12da-f463-4192-9800-d3ea50995ab8	f41acab0-d7a1-4441-942b-69664ceb9d3b	clock_in	email	t
8ac60c16-2880-48a8-8a30-5d5a883eb109	f41acab0-d7a1-4441-942b-69664ceb9d3b	clock_out	inapp	t
02a5f3a4-3ad2-4c70-b3ff-3c7ca336ce2d	f41acab0-d7a1-4441-942b-69664ceb9d3b	clock_out	whatsapp	t
b7b09298-61d2-4ae4-94f2-abfa6ce8c5f9	f41acab0-d7a1-4441-942b-69664ceb9d3b	clock_out	email	t
97528415-a800-42bd-9cdc-b230deffb7d4	f41acab0-d7a1-4441-942b-69664ceb9d3b	leave_request	inapp	t
5519df84-269a-4d2c-80d1-9f5b1b5ab744	f41acab0-d7a1-4441-942b-69664ceb9d3b	leave_request	whatsapp	t
958fb243-446f-4fea-b86e-4579c8995e55	f41acab0-d7a1-4441-942b-69664ceb9d3b	leave_request	email	t
00fb00de-89fb-4d6b-852d-86d75ce97a62	f41acab0-d7a1-4441-942b-69664ceb9d3b	incident	inapp	t
b641fba4-260a-412a-aede-25305f6eb7ac	f41acab0-d7a1-4441-942b-69664ceb9d3b	incident	whatsapp	t
3942a257-707e-48f0-93e9-74947af9eaa0	f41acab0-d7a1-4441-942b-69664ceb9d3b	incident	email	t
499ffecc-d3f2-4b84-8438-76ae878c9555	f41acab0-d7a1-4441-942b-69664ceb9d3b	document	inapp	t
afc9cd7a-7034-4561-bb47-76746ea92e70	f41acab0-d7a1-4441-942b-69664ceb9d3b	document	whatsapp	t
f234275a-d390-4948-9021-2a2f8c6e6522	f41acab0-d7a1-4441-942b-69664ceb9d3b	document	email	t
a17780c0-6234-42e6-b996-e5e7c7b4362a	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	email	f
3aaae545-c4d1-4d2a-b2d0-c3b528347d8a	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	email	f
bddc7f7c-6a4b-475f-849e-f24e6ee4a243	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	leave_request	email	f
a24ebd41-4779-490e-96df-9f88b0d228ac	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	incident	email	f
777161ae-1f2f-4413-9670-764072cc8c4c	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	document	email	f
170bc2bb-8c4d-4bd4-a446-96e6771da07e	c3136edf-351e-4329-8050-720ecd216410	clock_in	inapp	t
c1bd7554-f768-4735-a4c5-34e32d0cd456	c3136edf-351e-4329-8050-720ecd216410	clock_out	inapp	t
4dbc849f-6ce1-4eb0-8865-49ef59833303	c3136edf-351e-4329-8050-720ecd216410	clock_out	whatsapp	t
facde9ef-fb9a-4d75-a426-60b38ec25ac9	c3136edf-351e-4329-8050-720ecd216410	leave_request	inapp	t
cdcbc2fc-b5e5-4874-b714-8914789d6600	c3136edf-351e-4329-8050-720ecd216410	leave_request	whatsapp	t
85353b0f-b429-46bb-9dd1-47adfe002db7	c3136edf-351e-4329-8050-720ecd216410	incident	inapp	t
9c214a66-e83d-4bc8-a530-f1d45ed851d0	c3136edf-351e-4329-8050-720ecd216410	incident	whatsapp	t
e6a498bb-1dea-4db0-8edf-477844f4a7e0	c3136edf-351e-4329-8050-720ecd216410	document	inapp	t
3de0de43-c1ad-4fd1-ab2b-8519bb222958	c3136edf-351e-4329-8050-720ecd216410	document	whatsapp	t
da05f708-2cda-4a42-bc3b-053b165fc149	c3136edf-351e-4329-8050-720ecd216410	clock_in	whatsapp	f
d79ef185-faef-40b9-9b61-565861c93243	c3136edf-351e-4329-8050-720ecd216410	clock_in	email	f
90d54361-9028-40e9-aecb-606e96aa92a9	c3136edf-351e-4329-8050-720ecd216410	clock_out	email	f
a558481c-38db-42ab-9d0d-f3a93fc2a84a	c3136edf-351e-4329-8050-720ecd216410	leave_request	email	f
1730b6d0-352d-4609-b86f-3fd399f68aaa	c3136edf-351e-4329-8050-720ecd216410	incident	email	f
4d4a7777-db2a-4306-9d70-f12434306615	c3136edf-351e-4329-8050-720ecd216410	document	email	f
71614dcf-61b3-45b1-8abe-3452fe3cee18	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	whatsapp	t
7dd7b298-c8b4-4e3d-aad6-6ccdccdca608	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	whatsapp	t
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.notifications (id, tenant_id, employee_id, event_type, title, body, link, actor_name, read_at, created_at) FROM stdin;
d5f4c552-b2ad-44ae-a474-101de70e9832	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	Fichaje de salida — Benito	Benito ha fichado la salida.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-06 22:21:04.251315
672eca20-8d34-4bdf-9f5e-c32a8422819c	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-07 06:09:36.861163
726b935f-fef5-4948-8100-32726ae28891	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	Fichaje de salida — Benito	Benito ha fichado la salida.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-07 07:54:27.647421
c2543719-d591-494d-bf6a-9b1fe386d174	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	leave_request	Solicitud de permiso — Benito	Benito solicita permiso del 2026-06-15 al 2026-06-16 (2.0 días).	/app/permisos	Benito	\N	2026-06-07 08:24:02.397573
5b6613c8-23d0-4927-91eb-b5a01d78f50f	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-07 17:41:11.602772
4bba6b8c-a9ec-433d-b1cd-2839b67980b0	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	Fichaje de salida — Benito	Benito ha fichado la salida.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-07 17:50:05.766959
9319c8c8-b8c5-4efd-9b88-5512181fd822	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-08 11:21:24.157107
7f3ff838-fa8e-4b40-9390-908276575bb5	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	leave_request	Nueva solicitud de permiso [Baja] — Benito	Benito solicita permiso del 2026-06-12 al 2026-06-12 (1.0 días).	/app/permisos	Benito	\N	2026-06-08 16:42:34.378857
69a2edd5-7010-45f3-a778-b1ae227ab309	951a449d-5f92-49c5-aec3-b3de06c44bcf	ef3409d9-798e-468c-9934-0b80e1ff7dc2	leave_request	Nueva solicitud de permiso [Baja] — Benito	Benito solicita permiso del 2026-06-12 al 2026-06-12 (1.0 días).	/app/permisos	Benito	\N	2026-06-08 16:42:36.189958
a0edf05c-c535-4d4a-9d92-299548b49585	951a449d-5f92-49c5-aec3-b3de06c44bcf	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	leave_request	Nueva solicitud de permiso [Baja] — Benito	Benito solicita permiso del 2026-06-12 al 2026-06-12 (1.0 días).	/app/permisos	Benito	2026-06-08 17:16:28.985378	2026-06-08 16:42:36.186669
1cef66d6-8a8d-4518-abbd-7c74c33ac469	951a449d-5f92-49c5-aec3-b3de06c44bcf	f41acab0-d7a1-4441-942b-69664ceb9d3b	leave_request	Solicitud de permiso [Baja] aprobada	Tu permiso del 2026-06-12 al 2026-06-12 ha sido aprobada.	/app/permisos	\N	\N	2026-06-08 17:16:41.02612
d671ebc1-e926-459c-99cf-a29fdc6fe45c	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-11 07:19:30.309264
f4b513c6-57dd-498a-bd75-4e895a01c11f	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	Fichaje de salida — Benito	Benito ha fichado la salida.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-11 14:17:06.028096
c39b1433-8fa8-450d-97d1-37aae7e93688	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-11 21:17:37.224576
9ff359ba-8302-444e-a599-af8738bac8ab	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	Fichaje de salida — Benito	Benito ha fichado la salida.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-11 21:18:24.458075
ba831866-0f49-43dd-8991-e36a57201241	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-12 06:46:26.312783
f3e1235f-0e22-45c6-8483-8c3eda4c6e33	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_in	Fichaje de entrada — María Diaz Garrón	María Diaz Garrón ha fichado la entrada.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-12 11:22:06.079816
29f6a3f9-90af-4d8f-a529-4d079e6e9adc	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	leave_request	Nueva solicitud de permiso [Dias acumulados] — María Diaz Garrón	María Diaz Garrón solicita permiso del 2026-06-16 al 2026-06-16 (1.0 días).	/app/permisos	María Diaz Garrón	\N	2026-06-12 11:27:10.424652
9ecdb479-412d-443d-923d-67bfaea32be4	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	leave_request	Solicitud de permiso [Dias acumulados] aprobada	Tu permiso del 2026-06-16 al 2026-06-16 ha sido aprobada.	/app/permisos	\N	2026-06-12 11:34:35.013367	2026-06-12 11:27:48.884594
d69ef2aa-05dd-4f2c-8ca2-db3485fb7e8c	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	941a5698-80fc-41ec-87c7-1fe4fa28ba75	leave_request	Nueva solicitud de permiso [Dias acumulados] — María Diaz Garrón	María Diaz Garrón solicita permiso del 2026-06-16 al 2026-06-16 (1.0 días).	/app/permisos	María Diaz Garrón	2026-06-12 14:26:18.604553	2026-06-12 11:27:12.243938
ab36fe41-aeb3-476b-a1b7-59c2507092fb	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	Fichaje de salida — Benito	Benito ha fichado la salida.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-15 16:25:06.667762
dabafa18-e360-44f8-b107-bc4d96af544e	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-16 05:44:02.872325
606222d0-6f81-44b3-8c50-565b4af4708f	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	leave_request	Nueva solicitud de permiso [Vacaciones] — Benito	Benito solicita permiso del 2026-06-17 al 2026-06-19 (3.0 días).	/app/permisos	Benito	\N	2026-06-16 05:44:31.669876
1b59c669-bd51-419c-be15-2e5d66e0756b	951a449d-5f92-49c5-aec3-b3de06c44bcf	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	leave_request	Nueva solicitud de permiso [Vacaciones] — Benito	Benito solicita permiso del 2026-06-17 al 2026-06-19 (3.0 días).	/app/permisos	Benito	\N	2026-06-16 05:44:33.528292
3b07a1e7-9731-429d-92a6-33c49673fdc8	951a449d-5f92-49c5-aec3-b3de06c44bcf	ef3409d9-798e-468c-9934-0b80e1ff7dc2	leave_request	Nueva solicitud de permiso [Vacaciones] — Benito	Benito solicita permiso del 2026-06-17 al 2026-06-19 (3.0 días).	/app/permisos	Benito	\N	2026-06-16 05:44:33.53079
9b034067-3f1e-47d9-8033-a7e94e7a940d	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_in	Fichaje de entrada — María Diaz Garrón	María Diaz Garrón ha fichado la entrada.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-16 08:07:17.804309
dd5df9ca-9c48-4755-9302-ceff802ae504	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	leave_request	Nueva solicitud de permiso [Vacaciones] — Benito	Benito solicita permiso del 2026-07-01 al 2026-07-15 (11.0 días).	/app/permisos	Benito	\N	2026-06-16 08:13:42.101402
af565911-6124-4043-8570-64e91128e687	951a449d-5f92-49c5-aec3-b3de06c44bcf	b2ed8b1c-8bb0-4408-a88e-ad0efabfee40	leave_request	Nueva solicitud de permiso [Vacaciones] — Benito	Benito solicita permiso del 2026-07-01 al 2026-07-15 (11.0 días).	/app/permisos	Benito	\N	2026-06-16 08:13:43.955787
ac226475-7bab-4c8b-a886-6e6656cf07a0	951a449d-5f92-49c5-aec3-b3de06c44bcf	ef3409d9-798e-468c-9934-0b80e1ff7dc2	leave_request	Nueva solicitud de permiso [Vacaciones] — Benito	Benito solicita permiso del 2026-07-01 al 2026-07-15 (11.0 días).	/app/permisos	Benito	\N	2026-06-16 08:13:43.959273
61ffab78-14ac-4d64-a8a8-12f1a6da76ec	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_out	Fichaje de salida — María Diaz Garrón	María Diaz Garrón ha fichado la salida.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-16 12:44:17.312972
8e4145ba-a320-4adc-95c8-93530c7a77da	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	Fichaje de salida — Benito	Benito ha fichado la salida.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-16 16:15:43.869582
810c1f3d-0f85-4352-90d0-79675d999a1f	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-17 07:12:52.616139
f1912cb6-017f-4735-abc8-d18c398cda31	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_in	Fichaje de entrada — María Diaz Garrón	María Diaz Garrón ha fichado la entrada.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-17 07:28:22.445563
901b8d55-351a-4e65-b2f5-3d114ae963d1	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_out	Fichaje de salida — María Diaz Garrón	María Diaz Garrón ha fichado la salida.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-17 12:22:36.383985
b65c98b0-1569-405f-8a88-211fd0918ef1	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_out	Fichaje de salida — Benito	Benito ha fichado la salida.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-17 17:42:46.460388
a88642d2-f3c2-422e-9f9c-2f2208328fd3	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_in	Fichaje de entrada — María Diaz Garrón	María Diaz Garrón ha fichado la entrada.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-18 07:32:42.221367
acfd89c3-a04f-4e2f-aed0-8fb5f0b8fcba	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_out	Fichaje de salida — María Diaz Garrón	María Diaz Garrón ha fichado la salida.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-18 12:08:20.469739
05aaea00-f46e-4798-86d7-f33118b8d585	951a449d-5f92-49c5-aec3-b3de06c44bcf	07a4e70c-019f-4b5c-8f15-0c8cdf9bef51	clock_in	Fichaje de entrada — Benito	Benito ha fichado la entrada.	/app/fichajes?employee_id=f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	\N	2026-06-19 06:06:42.703657
91027da8-9c11-4fa9-a72f-5acf36971d62	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_in	Fichaje de entrada — Jairo Pineda Zapata	Jairo Pineda Zapata ha fichado la entrada.	/app/fichajes?employee_id=2e344a27-169d-44fa-8151-0e643749dc33	Jairo Pineda Zapata	\N	2026-06-19 07:05:46.851502
7ba7b329-7fb5-45cb-8819-b7ec477736c7	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	941a5698-80fc-41ec-87c7-1fe4fa28ba75	leave_request	Nueva solicitud de permiso [Vacaciones] — Carmen Docobo	Carmen Docobo solicita permiso del 2026-06-19 al 2026-06-19 (1.0 días).	/app/permisos	Carmen Docobo	\N	2026-06-19 07:23:05.370062
068f5fd4-3946-4eef-a124-5a6191287676	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	c3136edf-351e-4329-8050-720ecd216410	leave_request	Nueva solicitud de permiso [Vacaciones] — Carmen Docobo	Carmen Docobo solicita permiso del 2026-06-19 al 2026-06-19 (1.0 días).	/app/permisos	Carmen Docobo	\N	2026-06-19 07:23:05.371785
843953d6-457c-4fdd-be7f-5c9427ff21f2	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_in	Fichaje de entrada — María Diaz Garrón	María Diaz Garrón ha fichado la entrada.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-19 07:32:31.68028
5d9d41f2-a787-4f61-bae5-a24a01f15fd0	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_out	Fichaje de salida — María Diaz Garrón	María Diaz Garrón ha fichado la salida.	/app/fichajes?employee_id=c3136edf-351e-4329-8050-720ecd216410	María Diaz Garrón	\N	2026-06-19 12:03:35.965081
d58fee51-8f05-4882-8992-3f56de772f6e	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	e5e24f2f-86ec-4321-8853-e394a494630e	clock_out	Fichaje de salida — Jairo Pineda Zapata	Jairo Pineda Zapata ha fichado la salida.	/app/fichajes?employee_id=2e344a27-169d-44fa-8151-0e643749dc33	Jairo Pineda Zapata	\N	2026-06-19 19:56:22.502986
\.


--
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.password_reset_tokens (id, token, employee_id, expires_at, used, created_at) FROM stdin;
e73c7749-f0ae-4c50-933b-9f3e826faebd	vqBPtosd007Avm7h0au-nKr5vir9zYm1hz-2o1BvFzI	941a5698-80fc-41ec-87c7-1fe4fa28ba75	2026-06-12 16:22:10.370462	t	2026-06-12 16:07:10.370491
9411bc40-6ea0-4ed8-b5e3-b311afacd59f	6Ivva_JNZzEqIXfF1b1QEmVS0lXQg2dT3MRQJXdJO8s	941a5698-80fc-41ec-87c7-1fe4fa28ba75	2026-06-12 16:31:17.840361	t	2026-06-12 16:16:17.840403
\.


--
-- Data for Name: pending_signups; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.pending_signups (id, data_json, tenant_id, ls_subscription_id, status, error_message, created_at) FROM stdin;
\.


--
-- Data for Name: platform_policies; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.platform_policies (id, ai_monthly_limit, ai_limit_action, whatsapp_monthly_limit, whatsapp_limit_action, support_channel, support_email, support_notice, tos_notice, updated_at) FROM stdin;
\.


--
-- Data for Name: platform_settings; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.platform_settings (id, legal_name, tax_id, billing_address, billing_city, billing_postal_code, billing_province, billing_country, billing_email, billing_phone, website, iban, bank_name, swift_bic, invoice_prefix, invoice_next_number, invoice_current_year, vat_rate, invoice_footer_text, auto_send_invoice_email, updated_at, credit_note_prefix, credit_note_next_number, credit_note_current_year) FROM stdin;
00000000-0000-0000-0000-000000000001	Alcurro SL	28778763J	\N	\N	\N	\N	ES	\N	\N	\N	\N	\N	\N	ALC	5	2026	21	\N	t	2026-06-14 17:46:46.311872	ALC-R	3	2026
\.


--
-- Data for Name: platform_users; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.platform_users (id, email, full_name, password_hash, is_active, created_at) FROM stdin;
c6da00ff-0b3e-4a7e-b7b9-e66a30ef9db0	platform@hrm.local	Administrador Plataforma	$2b$12$L6RjCKG5.nPio5yB5u5QY.fSvdORBR5kVR1izHSJxkqJq2/cInDz2	t	2026-05-25 19:03:01.830908
5d10df3e-bddb-4614-b238-079f20fd5bd1	beni4041@gmail.com	Benito	$2b$12$UU2hLFwmDxg6npK.YYyqkukH7nz8V50xW/rcAPdJJSJRyc6DSZKa.	t	2026-05-25 19:20:24.764634
\.


--
-- Data for Name: pricing_plans; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.pricing_plans (id, code, name, description, monthly_price_cents, annual_price_cents, max_active_users, currency, is_active, sort_order, stripe_product_id, stripe_price_monthly_id, stripe_price_annual_id, created_at, updated_at, ls_variant_id_monthly, ls_variant_id_annual, ls_product_id) FROM stdin;
47cfafa4-a8c2-4fd3-adbb-4e44780a5942	basica	Básica	Hasta 3 usuarios activos. 18€/mes o 15€/mes con contrato anual.	1800	18000	3	EUR	f	0	\N	\N	\N	2026-05-25 19:03:06.402942	2026-06-13 20:16:48.695749	\N	\N	\N
e776cd4f-ac29-426c-ab41-759f588c83c5	micro	micro	de 0 a 3 empleados activos	2500	27504	3	EUR	t	0	prod_Uf470fWnm7ebAP	price_1Tfjz820HNFQXDpepJuUhGW6	price_1Tfjz820HNFQXDpeRt3Z4j8Y	2026-06-07 16:50:15.193164	2026-06-14 07:39:37.604618	1786872	1788057	\N
cad25f60-dbbb-4b5d-9b9c-245fdb7be3ab	equipo	equipo	de 4 a 10 empleados	6000	66000	10	EUR	t	1	\N	\N	\N	2026-06-07 16:59:49.85919	2026-06-14 07:45:45.062651	1788060	1788069	\N
844cec6b-d77f-401d-a5f8-acc70edfecb1	plantilla	plantilla	de 11 a 25 trabajadores	7500	82500	25	EUR	t	5	\N	\N	\N	2026-06-07 17:00:40.5491	2026-06-14 07:47:35.934806	1788086	1788089	\N
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.projects (id, company_id, name, code, address, planned_hours, is_active, active_for_clock, created_at, updated_at) FROM stdin;
a145d4f4-3f15-4c23-93bc-51a09947a031	ec0da4d5-072b-4ede-85d3-439c47fc7e44	PORTAL	PRY-001	\N	1250	t	t	2026-05-26 09:38:26.344326	2026-05-26 09:38:32.504534
054c928c-0a9e-4014-9daa-c012d6113c5f	ec0da4d5-072b-4ede-85d3-439c47fc7e44	LOS PRINCIPES	PRY-002	\N	\N	t	t	2026-06-11 05:11:23.874006	2026-06-11 05:11:23.874028
\.


--
-- Data for Name: shift_assignments; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.shift_assignments (id, employee_id, shift_configuration_id, valid_from, valid_to, calendar_overrides, created_at) FROM stdin;
\.


--
-- Data for Name: shift_configurations; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.shift_configurations (id, company_id, name, pattern_type, description, weekly_hours, pattern_definition, default_start_time, default_end_time, is_active, created_at) FROM stdin;
7a4d2d89-c8b3-41e7-b12a-0bd8dab1aaee	f13fda9a-7d23-4597-86e9-2bcfadc2c677	Oficina L-V 8-17	RIGID	\N	40	{"slots": [{"day": 0, "start": "08:00", "end": "17:00"}, {"day": 1, "start": "08:00", "end": "17:00"}, {"day": 2, "start": "08:00", "end": "17:00"}, {"day": 3, "start": "08:00", "end": "17:00"}, {"day": 4, "start": "08:00", "end": "17:00"}]}	\N	\N	t	2026-05-25 19:19:33.554698
\.


--
-- Data for Name: signature_envelopes; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.signature_envelopes (id, tenant_id, document_delivery_id, reference, title, status, original_path, original_hash, signed_path, signed_hash, certificate_path, certificate_json_path, expires_at, completed_at, cancelled_at, cancel_reason, created_at, updated_at) FROM stdin;
87708f6e-9fe6-4091-a034-021d40f3a32e	951a449d-5f92-49c5-aec3-b3de06c44bcf	070213a7-5aad-4269-9bd3-93dd897463c3	FRM-20260608-160419	Firma de prueba	cancelado	/app/uploads/legal/89da83de-81f8-4735-90c3-35b2d948a774_legal_Normativa_interna_y_uso_de_medios_digita_v1.pdf	413b0dc46f5be69ad62bc740a516f5d1372ace93cba9d55548f6437ea2e206ce	\N	\N	\N	\N	2026-06-22 16:04:19.359132	\N	2026-06-08 16:06:27.337183	confundido dni	2026-06-08 16:04:19.359424	2026-06-08 16:06:27.337218
aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	951a449d-5f92-49c5-aec3-b3de06c44bcf	070213a7-5aad-4269-9bd3-93dd897463c3	FRM-20260608-160708	firma de prueba	completado	/app/uploads/legal/89da83de-81f8-4735-90c3-35b2d948a774_legal_Normativa_interna_y_uso_de_medios_digita_v1.pdf	413b0dc46f5be69ad62bc740a516f5d1372ace93cba9d55548f6437ea2e206ce	/app/uploads/firma/envelope-aa0f22c7-b9bc-405c-ac6c-88724a61bbc4/FRM-20260608-160708_signed.pdf	691b8e8f180bb665c34f984932998c835d06abddc195b9da75ecf531fe89ced9	/app/uploads/firma/envelope-aa0f22c7-b9bc-405c-ac6c-88724a61bbc4/FRM-20260608-160708_cert.pdf	/app/uploads/firma/envelope-aa0f22c7-b9bc-405c-ac6c-88724a61bbc4/FRM-20260608-160708_cert.json	2026-06-22 16:07:08.243914	2026-06-08 16:09:43.11682	\N	\N	2026-06-08 16:07:08.24407	2026-06-08 16:09:45.323172
\.


--
-- Data for Name: signature_events; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.signature_events (id, envelope_id, event_type, payload_json, prev_hash, event_hash, created_at) FROM stdin;
26b25067-561d-4254-9a5c-996294aaa765	87708f6e-9fe6-4091-a034-021d40f3a32e	envelope_created	{"reference": "FRM-20260608-160419", "original_hash": "413b0dc46f5be69ad62bc740a516f5d1372ace93cba9d55548f6437ea2e206ce"}	\N	3bb9e393c0590783e1c03060eba3ad67a13f416771b067c26e540f42d21b3256	2026-06-08 16:04:19.370011
efdefe29-4b02-4a7f-a860-5091a378d7d6	87708f6e-9fe6-4091-a034-021d40f3a32e	signer_added	{"signer_id": "fa23b2c7-8846-4c7a-b52a-50e944d144e0", "name": "Benito"}	3bb9e393c0590783e1c03060eba3ad67a13f416771b067c26e540f42d21b3256	01b04a552bcb789dfbb945cc4221b41b5ffac42cabb2f1ac9e125f6fcb896702	2026-06-08 16:04:19.382336
acce3127-604c-489b-a841-56db31084a0f	87708f6e-9fe6-4091-a034-021d40f3a32e	signer_added	{"signer_id": "1346bc4b-29fd-438c-a1ff-552c823707db", "name": "Lucía"}	01b04a552bcb789dfbb945cc4221b41b5ffac42cabb2f1ac9e125f6fcb896702	a10ed0611a0ce35cde283e2b50146862aa768ba98a235990a2fe8c25f49dca30	2026-06-08 16:04:19.385923
3ba23531-6e0b-4088-92f8-5560e6187aa6	87708f6e-9fe6-4091-a034-021d40f3a32e	envelope_sent	{}	a10ed0611a0ce35cde283e2b50146862aa768ba98a235990a2fe8c25f49dca30	c34e35b68df99100dcbefb1c0b527d5fd0e9aba11b39707f6decad41c0f4e0e5	2026-06-08 16:04:22.456318
d1304491-ba85-418d-829b-8513b8e6e63c	87708f6e-9fe6-4091-a034-021d40f3a32e	signer_resent	{"signer_id": "1346bc4b-29fd-438c-a1ff-552c823707db"}	c34e35b68df99100dcbefb1c0b527d5fd0e9aba11b39707f6decad41c0f4e0e5	013523870f9c80313a3fd02faa4987351c750929f8ecc1e0a6bfe482b1d974ff	2026-06-08 16:04:47.307773
2cde5d01-09ac-4f12-b358-b443c5f3ff53	87708f6e-9fe6-4091-a034-021d40f3a32e	otp_issued	{"signer_id": "fa23b2c7-8846-4c7a-b52a-50e944d144e0"}	013523870f9c80313a3fd02faa4987351c750929f8ecc1e0a6bfe482b1d974ff	bc3ccb4df0e93db39b639e8027c01d5bbe8d6cc24942e88ec4170796306e92e9	2026-06-08 16:05:35.636799
4fb9e398-f73e-4215-995a-f0406b15288d	87708f6e-9fe6-4091-a034-021d40f3a32e	otp_verified	{"signer_id": "fa23b2c7-8846-4c7a-b52a-50e944d144e0"}	bc3ccb4df0e93db39b639e8027c01d5bbe8d6cc24942e88ec4170796306e92e9	f02ae038f3ca29f3cdec50463c8309956e46c61544657fa5393dcf31f95c968e	2026-06-08 16:05:44.621073
01e8016f-b505-4fa4-bc6b-2c984dbd0238	87708f6e-9fe6-4091-a034-021d40f3a32e	document_signed	{"signer_id": "fa23b2c7-8846-4c7a-b52a-50e944d144e0", "name": "Benito", "ip": "193.125.14.175"}	f02ae038f3ca29f3cdec50463c8309956e46c61544657fa5393dcf31f95c968e	f2d7eb3989dd909479eed68a32dcde8b475967b388ee200b768ece4544bef519	2026-06-08 16:05:57.123356
b4d95191-e14e-42c4-a182-6e3c6a4312a5	87708f6e-9fe6-4091-a034-021d40f3a32e	envelope_cancelled	{"reason": "confundido dni"}	f2d7eb3989dd909479eed68a32dcde8b475967b388ee200b768ece4544bef519	8b86f8666fd3b266f5260b3c8e1116687e445aed375f602bb42bea301bce9fd6	2026-06-08 16:06:27.3414
ddfe6b34-8ec0-45ea-9433-0c447ba56a9a	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	envelope_created	{"reference": "FRM-20260608-160708", "original_hash": "413b0dc46f5be69ad62bc740a516f5d1372ace93cba9d55548f6437ea2e206ce"}	\N	d3884f3d0b5c3a1b9e90e1ad43f8b31eeb556e095fe52da05ad375ef6bb113ab	2026-06-08 16:07:08.246303
e762dddc-ded5-4b99-8c91-21ba6b323a44	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	signer_added	{"signer_id": "b155403b-dbd7-4075-9ad8-b4b6b618cb73", "name": "Lucía"}	d3884f3d0b5c3a1b9e90e1ad43f8b31eeb556e095fe52da05ad375ef6bb113ab	1526cb7a67916b41be8581fe1f194d83f55d3fee2bf1b4379b0bd30eb652d304	2026-06-08 16:07:08.249067
88682091-d1d3-4514-a476-7af78300742c	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	signer_added	{"signer_id": "e84889a7-47ce-4169-b90b-31d6eba68efe", "name": "Benito"}	1526cb7a67916b41be8581fe1f194d83f55d3fee2bf1b4379b0bd30eb652d304	f41a31a010bd249ad0e242383e62474592546ab052b1ee3f32a50f5617b56efb	2026-06-08 16:07:08.252808
54c52293-4f42-47df-8fa0-2c4b6ddcd313	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	envelope_sent	{}	f41a31a010bd249ad0e242383e62474592546ab052b1ee3f32a50f5617b56efb	e369810308c73f47711e3cd72ad3367616985184f3bc943feef112f91b783310	2026-06-08 16:07:11.900938
288e703a-c3a2-446f-9210-54c44b318e37	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	otp_issued	{"signer_id": "e84889a7-47ce-4169-b90b-31d6eba68efe"}	e369810308c73f47711e3cd72ad3367616985184f3bc943feef112f91b783310	9cbcc953111041cc46df2b14c18b3c36b94b6d535be8c2ef3f1ef7f2d6876dd1	2026-06-08 16:07:31.661363
df01cb58-57e6-41ee-8c8f-c9c46e3474d6	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	otp_verified	{"signer_id": "e84889a7-47ce-4169-b90b-31d6eba68efe"}	9cbcc953111041cc46df2b14c18b3c36b94b6d535be8c2ef3f1ef7f2d6876dd1	373a9d4fc1a60cb8782698662f0444946f674c11e43a2e8eb314198811ad41d2	2026-06-08 16:07:40.754612
ecf7abb0-bd55-4c50-83c7-5a57f702a1e1	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	document_signed	{"signer_id": "e84889a7-47ce-4169-b90b-31d6eba68efe", "name": "Benito", "ip": "193.125.14.175"}	373a9d4fc1a60cb8782698662f0444946f674c11e43a2e8eb314198811ad41d2	472c81028f9f5e9810145885875297650f9e190576804f946fc8af849217f1ad	2026-06-08 16:07:44.193154
a1a3aa2f-2152-4052-b2aa-aef416aacca1	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	otp_issued	{"signer_id": "b155403b-dbd7-4075-9ad8-b4b6b618cb73"}	472c81028f9f5e9810145885875297650f9e190576804f946fc8af849217f1ad	8f9fc2906bc50b9d6099a9b73bb4fa81d6cd9fc13b951d903631c2785b09a0a5	2026-06-08 16:07:46.081403
7af18d3d-92ab-490c-9976-80e12227529d	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	otp_verified	{"signer_id": "b155403b-dbd7-4075-9ad8-b4b6b618cb73"}	8f9fc2906bc50b9d6099a9b73bb4fa81d6cd9fc13b951d903631c2785b09a0a5	bffc6b16e0db66bac6d534424fd54cba0393a34a70c20b095ddd5a61834adebf	2026-06-08 16:08:06.680185
159c6456-ffe3-4c47-9931-fe9d16e73d64	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	otp_issued	{"signer_id": "b155403b-dbd7-4075-9ad8-b4b6b618cb73"}	bffc6b16e0db66bac6d534424fd54cba0393a34a70c20b095ddd5a61834adebf	1dba3e42b599c6f9c97fdd36ce35c574f53fb17c63f81630077c0ea388096265	2026-06-08 16:09:02.14373
56c0c12d-2522-4097-8466-606759f23826	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	otp_verified	{"signer_id": "b155403b-dbd7-4075-9ad8-b4b6b618cb73"}	1dba3e42b599c6f9c97fdd36ce35c574f53fb17c63f81630077c0ea388096265	5f98c7ec11195689be2164bfecbd5b3832443bcea479fe57a0a6ae9d39e27672	2026-06-08 16:09:33.716346
4962ffc6-a588-42dd-970a-9f1eca6f03c4	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	document_signed	{"signer_id": "b155403b-dbd7-4075-9ad8-b4b6b618cb73", "name": "Lucía", "ip": "193.125.14.175"}	5f98c7ec11195689be2164bfecbd5b3832443bcea479fe57a0a6ae9d39e27672	9b5ddebfbcd5b76d04368018ed8361c11f918770a434f5ec8076de8ce8bb6304	2026-06-08 16:09:43.019326
21caa281-8ee5-45b9-b4b9-4583f8426f69	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	envelope_completed	{"signed_hash": "691b8e8f180bb665c34f984932998c835d06abddc195b9da75ecf531fe89ced9"}	9b5ddebfbcd5b76d04368018ed8361c11f918770a434f5ec8076de8ce8bb6304	a11713e9f73d0508cb74aa0c30b590906cc2fc2ac57342236ec75713ef3f35d9	2026-06-08 16:09:43.120452
\.


--
-- Data for Name: signature_notifications; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.signature_notifications (id, envelope_id, signer_id, channel, event_type, success, detail, created_at) FROM stdin;
1a6feb40-aa98-46e4-9323-6bb5b0857ced	87708f6e-9fe6-4091-a034-021d40f3a32e	fa23b2c7-8846-4c7a-b52a-50e944d144e0	whatsapp	solicitud	t	\N	2026-06-08 16:04:19.919165
4dfc646d-dfdc-4124-9734-2539dcb0961f	87708f6e-9fe6-4091-a034-021d40f3a32e	fa23b2c7-8846-4c7a-b52a-50e944d144e0	email	solicitud	t	\N	2026-06-08 16:04:20.846721
dfcb1a8d-0613-4455-a75b-db2dc3d61cf7	87708f6e-9fe6-4091-a034-021d40f3a32e	1346bc4b-29fd-438c-a1ff-552c823707db	whatsapp	solicitud	t	\N	2026-06-08 16:04:21.563761
558ac6fb-200b-441d-aeea-6e7086aa9f4e	87708f6e-9fe6-4091-a034-021d40f3a32e	1346bc4b-29fd-438c-a1ff-552c823707db	email	solicitud	t	\N	2026-06-08 16:04:22.451033
461a3253-e3c4-4151-aa8d-1e535d67a46c	87708f6e-9fe6-4091-a034-021d40f3a32e	1346bc4b-29fd-438c-a1ff-552c823707db	whatsapp	solicitud	t	\N	2026-06-08 16:04:47.829256
be9fdc67-f918-4bad-91c3-9239c76e9e69	87708f6e-9fe6-4091-a034-021d40f3a32e	1346bc4b-29fd-438c-a1ff-552c823707db	email	solicitud	t	\N	2026-06-08 16:04:48.731424
84b924fa-68d7-44f1-992a-39e7cfd04bea	87708f6e-9fe6-4091-a034-021d40f3a32e	fa23b2c7-8846-4c7a-b52a-50e944d144e0	whatsapp	otp	t	\N	2026-06-08 16:05:36.147555
51f2bc1e-355c-44e5-846c-94a29cf0eee8	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	b155403b-dbd7-4075-9ad8-b4b6b618cb73	whatsapp	solicitud	t	\N	2026-06-08 16:07:09.251302
1c2f9a48-5598-44df-8cf9-e18119a136e0	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	b155403b-dbd7-4075-9ad8-b4b6b618cb73	email	solicitud	t	\N	2026-06-08 16:07:10.128581
a2a0b748-8799-412e-9e0c-1ade75e1954d	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	e84889a7-47ce-4169-b90b-31d6eba68efe	whatsapp	solicitud	t	\N	2026-06-08 16:07:11.03911
51fa51a8-f890-4ebd-890b-de951fc6279a	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	e84889a7-47ce-4169-b90b-31d6eba68efe	email	solicitud	t	\N	2026-06-08 16:07:11.897476
6efdf6ee-5785-4068-917d-f1c8020221c1	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	e84889a7-47ce-4169-b90b-31d6eba68efe	whatsapp	otp	t	\N	2026-06-08 16:07:32.55573
95a31343-908b-4b5f-bbb5-7b4dfd1affbe	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	b155403b-dbd7-4075-9ad8-b4b6b618cb73	whatsapp	otp	t	\N	2026-06-08 16:07:47.308556
a6811daf-a71c-43f2-8e61-453c22a885af	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	b155403b-dbd7-4075-9ad8-b4b6b618cb73	whatsapp	otp	t	\N	2026-06-08 16:09:03.317194
98511238-e2ac-4fa5-97ab-ccde46b962e2	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	b155403b-dbd7-4075-9ad8-b4b6b618cb73	whatsapp	completada	t	\N	2026-06-08 16:09:44.350261
426d327c-e851-4022-ab3c-fa1f38da5822	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	e84889a7-47ce-4169-b90b-31d6eba68efe	whatsapp	completada	t	\N	2026-06-08 16:09:45.323062
\.


--
-- Data for Name: signature_otps; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.signature_otps (id, signer_id, code_hash, expires_at, attempts, used_at, created_at) FROM stdin;
54bf8220-b036-471b-bd59-059843465259	fa23b2c7-8846-4c7a-b52a-50e944d144e0	78b46352829da87464ea796198e7ba84e7858f00baaa90151d74bfd7071a869c	2026-06-08 16:15:35.631469	1	2026-06-08 16:05:44.616388	2026-06-08 16:05:35.631653
dd024bcd-e0e9-4443-8618-7a82c7da38fe	e84889a7-47ce-4169-b90b-31d6eba68efe	07aa59109c36d8aecc10f723f4641ef93d97663ed2d0617032dfdbf3657d9d34	2026-06-08 16:17:31.658031	1	2026-06-08 16:07:40.75208	2026-06-08 16:07:31.65818
6a5b25ac-f236-47af-8c41-a119167fb7d3	b155403b-dbd7-4075-9ad8-b4b6b618cb73	7b18587ed334946c10752e3983ee81e6b3d74a86146db5400005814c8f9ebced	2026-06-08 16:17:46.078828	1	2026-06-08 16:08:06.677839	2026-06-08 16:07:46.079005
e77981f0-2fbe-454f-bcc2-939f812c3016	b155403b-dbd7-4075-9ad8-b4b6b618cb73	b3081ef4c4c02ef241fc92c1a476249b539486cc070422e051d6aad3838b1e5c	2026-06-08 16:19:02.137926	1	2026-06-08 16:09:33.713435	2026-06-08 16:09:02.138165
\.


--
-- Data for Name: signature_signers; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.signature_signers (id, envelope_id, employee_id, full_name, email, phone, id_document, sign_order, status, token_hash, token_plain, otp_verified_at, signed_at, signature_path, signer_name, ip_address, user_agent, created_at) FROM stdin;
fa23b2c7-8846-4c7a-b52a-50e944d144e0	87708f6e-9fe6-4091-a034-021d40f3a32e	f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	beni4041@gmail.com	34624230960	28778763J	1	firmado	057152677cc3a86c6982faf213dd8e96fe7c177ba62f21ac9d9ab63c19d15386	\N	2026-06-08 16:05:44.616414	2026-06-08 16:05:57.12076	/app/uploads/firma/envelope-87708f6e-9fe6-4091-a034-021d40f3a32e/signatures/signer-fa23b2c7-8846-4c7a-b52a-50e944d144e0.png	Benito	193.125.14.175	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-08 16:04:19.374692
1346bc4b-29fd-438c-a1ff-552c823707db	87708f6e-9fe6-4091-a034-021d40f3a32e	\N	Lucía	lblr81@gmail.com	34679324504	28811323	2	expirado	055d17876c7c90228ae660e3f26990d2ee30dbad7635fdd3ec49af5e4e08d953	\N	\N	\N	\N	\N	\N	\N	2026-06-08 16:04:19.3836
e84889a7-47ce-4169-b90b-31d6eba68efe	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	f41acab0-d7a1-4441-942b-69664ceb9d3b	Benito	beni4041@gmail.com	34624230960	28778763J	2	firmado	629f2406a745e39eb618b2b6511da110cc415ce5d616188c5db3b46ae6ba2637	\N	2026-06-08 16:07:40.752099	2026-06-08 16:07:44.190886	/app/uploads/firma/envelope-aa0f22c7-b9bc-405c-ac6c-88724a61bbc4/signatures/signer-e84889a7-47ce-4169-b90b-31d6eba68efe.png	Benito	193.125.14.175	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-08 16:07:08.251019
b155403b-dbd7-4075-9ad8-b4b6b618cb73	aa0f22c7-b9bc-405c-ac6c-88724a61bbc4	\N	Lucía	lblr81@gmail.com	34679324504	28811323M	1	firmado	40e47e801496def37541e5cc2e8be774b5d5c5f5314cfd38b9af8ff5bddde463	\N	2026-06-08 16:09:33.713461	2026-06-08 16:09:43.017296	/app/uploads/firma/envelope-aa0f22c7-b9bc-405c-ac6c-88724a61bbc4/signatures/signer-b155403b-dbd7-4075-9ad8-b4b6b618cb73.png	Lucía	193.125.14.175	Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36	2026-06-08 16:07:08.247279
\.


--
-- Data for Name: stripe_payments; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.stripe_payments (id, tenant_id, subscription_id, stripe_payment_intent_id, stripe_invoice_id, stripe_checkout_session_id, amount_cents, currency, status, description, paid_at, created_at, invoice_pdf_url, invoice_url, invoice_number) FROM stdin;
f492891a-882a-4b62-864c-35004a2b845e	951a449d-5f92-49c5-aec3-b3de06c44bcf	bd1742f9-f5e7-419c-89d5-19c7d40af894	pi_sim_a2928001792d45b6	\N	sim_a41e6ba5e6cf418f94f8241af8546cc8	1800	EUR	SUCCEEDED	Pago simulado (modo prueba)	2026-05-25 20:03:04.531546	2026-05-25 20:03:04.531722	\N	\N	\N
\.


--
-- Data for Name: subscriptions; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.subscriptions (id, tenant_id, company_id, pricing_plan_id, discount_id, plan_code, plan_name, status, amount_cents, currency, billing_cycle, billing_method_id, current_period_start, current_period_end, stripe_subscription_id, stripe_checkout_session_id, created_at, updated_at, pending_plan_id, pending_billing_cycle, ls_subscription_id, payment_failure_count, last_payment_failure_at) FROM stdin;
4dda8007-25b8-40b4-86ef-0fd495dc8a10	cf26f84d-f21f-4138-a024-e6ce33797ffd	f13fda9a-7d23-4597-86e9-2bcfadc2c677	47cfafa4-a8c2-4fd3-adbb-4e44780a5942	\N	basica	Básica	TRIALING	1800	EUR	monthly	\N	\N	\N	\N	\N	2026-05-25 19:03:04.93406	2026-05-25 19:03:04.934076	\N	\N	\N	0	\N
9865ec57-73f4-420e-ab92-b35c33a8613e	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	78fe1d81-289a-44c5-9897-eb3a2689ae56	cad25f60-dbbb-4b5d-9b9c-245fdb7be3ab	0babd662-7bde-4cfa-a582-f3fc738d8996	equipo	equipo	ACTIVE	600	EUR	monthly	\N	2026-06-14	2026-07-14	\N	\N	2026-06-14 17:45:13.463374	2026-06-14 17:45:13.463391	844cec6b-d77f-401d-a5f8-acc70edfecb1	monthly	2259564	0	\N
530d9f96-d8f9-4429-980e-87f0955bad16	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	376289a5-f76d-42e5-a07e-d266ec828caa	844cec6b-d77f-401d-a5f8-acc70edfecb1	\N	plantilla	plantilla	TRIALING	7500	EUR	monthly	\N	\N	\N	\N	\N	2026-06-12 11:31:00.487951	2026-06-17 09:27:29.981583	cad25f60-dbbb-4b5d-9b9c-245fdb7be3ab	monthly	\N	0	\N
49e78614-7f71-4ef0-865c-7593c91f45fe	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	35694ea1-39a1-4a90-99c9-2616c4b1adf1	e776cd4f-ac29-426c-ab41-759f588c83c5	\N	micro	micro	TRIALING	2500	EUR	monthly	\N	\N	\N	\N	\N	2026-06-12 11:31:20.723945	2026-06-12 11:31:20.723962	\N	\N	\N	0	\N
bd1742f9-f5e7-419c-89d5-19c7d40af894	951a449d-5f92-49c5-aec3-b3de06c44bcf	ec0da4d5-072b-4ede-85d3-439c47fc7e44	844cec6b-d77f-401d-a5f8-acc70edfecb1	0babd662-7bde-4cfa-a582-f3fc738d8996	plantilla	plantilla	ACTIVE	375	EUR	monthly	\N	\N	\N	sub_sim_a2928001792d45b6	sim_a41e6ba5e6cf418f94f8241af8546cc8	2026-05-25 20:02:55.922061	2026-06-12 14:37:21.991718	\N	\N	\N	0	\N
67eb3e31-37a3-463b-94f1-4917d0d6ee30	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	bb7211f4-1102-4865-a44c-cebcf8f075c8	cad25f60-dbbb-4b5d-9b9c-245fdb7be3ab	0babd662-7bde-4cfa-a582-f3fc738d8996	equipo	equipo	ACTIVE	500	EUR	monthly	\N	\N	\N	\N	cs_test_a19uT4alFYW505XglifxkHiDIZxecKgfztN0Xw8ZZ5NJcioNUEvzSHWtoN	2026-06-07 16:55:41.574898	2026-06-12 17:15:34.579017	cad25f60-dbbb-4b5d-9b9c-245fdb7be3ab	monthly	\N	0	\N
8673b323-54b0-4a5a-9388-fcce84efeb6d	bdd57572-5518-48c0-9e27-b9f2c23591de	4553c7c5-ec1f-4273-8053-4498eccd7f63	cad25f60-dbbb-4b5d-9b9c-245fdb7be3ab	0babd662-7bde-4cfa-a582-f3fc738d8996	equipo	equipo	TRIALING	600	EUR	monthly	\N	\N	\N	\N	\N	2026-06-14 17:37:01.247361	2026-06-14 17:37:01.247388	\N	\N	\N	0	\N
\.


--
-- Data for Name: system_settings; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.system_settings (id, gowa_send_url, gowa_basic_auth, gowa_webhook_url, gowa_ui_url, gowa_device_id, ollama_base_url, ollama_model, company_name, smtp_host, smtp_port, smtp_user, smtp_password, smtp_use_tls, mail_from_address, mail_from_name, updated_at) FROM stdin;
1	http://gowa:3000/send/message	admin:admin	http://backend:8000/webhook/whatsapp	http://localhost:3000	3b0ec19e-9da4-4183-8aa9-309f9d14a4c9	http://ollama:11434	llama3.2	Mi Empresa	smtp.ionos.es	587	info@alcurro.es	Boliche-0064	t	info@alcurro.es	alcurro - RRHH	2026-05-25 19:20:38.191261
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.tenants (id, slug, name, is_active, legal_name, tax_id, billing_email, billing_phone, billing_address, billing_city, billing_postal_code, billing_province, billing_country, logo_url, primary_color, secondary_color, accent_color, gowa_container_name, gowa_host, gowa_port, gowa_send_url, gowa_ui_url, gowa_basic_auth, gowa_webhook_path, gowa_device_id, gowa_status, gowa_error, ollama_base_url, ollama_model, stripe_customer_id, created_at, updated_at, billing_company_id, ls_customer_id, ls_customer_portal_url) FROM stdin;
cf26f84d-f21f-4138-a024-e6ce33797ffd	demo	Cuenta Demo	t	\N	\N	\N	\N	\N	\N	\N	\N	ES	\N	#3b82f6	#1e2a3a	#22c55e	\N		\N			admin:admin	/webhook/whatsapp/demo	\N	PENDING	\N	http://ollama:11434	qwen2.5:7b	\N	2026-05-25 18:50:53.599279	2026-05-25 18:50:53.599299	\N	\N	\N
bdd57572-5518-48c0-9e27-b9f2c23591de	prueba-liano	prueba liaño	t	prueba liaño	B90000092	lblr81@gmail.com	679324504	\N	\N	\N	\N	ES	\N	#3b82f6	#1e2a3a	#22c55e	\N		\N			admin:admin	/webhook/whatsapp/prueba-liano	\N	PENDING	\N	http://ollama:11434	llama3.2	\N	2026-06-14 17:37:01.223507	2026-06-14 17:37:01.223536	4553c7c5-ec1f-4273-8053-4498eccd7f63	\N	\N
cbbf551f-87c4-47f4-aa8b-cd20e7036a61	puerta-sevilla	Puerta Sevilla	t	Puerta Sevilla inmobiliaria	B90000092	benito.barrios@dealerbest.com	685084165	Pinzones 2	Sevilla	41008	Sevilla	ES	/uploads/branding/cbbf551f-87c4-47f4-aa8b-cd20e7036a61/logo.png	#3b82f6	#1e2a3a	#22c55e	\N		\N			admin:admin	/webhook/whatsapp/puerta-sevilla	\N	PENDING	\N	http://ollama:11434	llama3.2	cus_Uf47tIRJgQH9I8	2026-06-07 16:55:41.557533	2026-06-07 16:55:41.557552	bb7211f4-1102-4865-a44c-cebcf8f075c8	\N	\N
951a449d-5f92-49c5-aec3-b3de06c44bcf	jjac	Jjac	t	Jonatan Luna	B9000	info@jjac.es	699999999	Av. Cantalobos	Sevilla	41008	Sevilla	ES	\N	#3b82f6	#1e2a3a	#22c55e	\N		\N			admin:admin	/webhook/whatsapp/jjac	\N	PENDING	\N	http://ollama:11434	qwen2.5:7b	cus_sim_a2928001792d45b6	2026-05-25 20:02:55.905709	2026-05-25 20:02:55.905733	ec0da4d5-072b-4ede-85d3-439c47fc7e44	\N	\N
deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	prueba-liano-2	prueba liaño 2	t	prueba liaño 2	B90000093	lblr81@gmail.com	679324504	\N	\N	\N	\N	ES	\N	#3b82f6	#1e2a3a	#22c55e	\N		\N			admin:admin	/webhook/whatsapp/prueba-liano-2	\N	PENDING	\N	http://ollama:11434	llama3.2	\N	2026-06-14 17:45:13.443927	2026-06-14 17:45:13.443945	78fe1d81-289a-44c5-9897-eb3a2689ae56	9025567	https://alcurro.lemonsqueezy.com/billing?expires=1781483865&store_domain=alcurro.lemonsqueezy.com&test_mode=1&user=7388737&signature=e8bb62cc74ba55cfb381e5b5d5e916473af7e24478b20e6d49fe49bbc13d90bb
\.


--
-- Data for Name: user_groups; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.user_groups (id, tenant_id, name, description, is_system, permissions, created_at, updated_at) FROM stdin;
91bfcade-42f1-4d16-933f-28822a4142e8	cf26f84d-f21f-4138-a024-e6ce33797ffd	Empleados con panel	Consulta de fichajes y vacaciones propias	t	["breaks.create_own", "breaks.read_own", "clock_ins.create_own", "clock_ins.read_own", "documents.read_own", "leave.create_own", "leave.read_own", "leave.update_own", "legal.read", "legal.read_own", "legal.update_own", "signatures.read_own"]	2026-05-25 19:03:03.399891	2026-05-25 19:03:03.399905
aed12517-3a64-42a8-bae1-0bb73f71e679	cf26f84d-f21f-4138-a024-e6ce33797ffd	Administradores de cuenta	Control total del tenant: empresas, centros, departamentos y configuración	t	["breaks.create_own", "breaks.read", "breaks.read_own", "breaks.update_own", "breaks.write", "clock_ins.create_own", "clock_ins.read", "clock_ins.read_own", "clock_ins.update_own", "clock_ins.write", "companies.read", "companies.write", "departments.read", "departments.write", "documents.bulk", "documents.create_own", "documents.read", "documents.read_own", "documents.update_own", "documents.write", "employees.create_own", "employees.delete", "employees.read", "employees.read_own", "employees.update_own", "employees.write", "gowa.manage", "groups.read", "groups.write", "leave.approve", "leave.create_own", "leave.read", "leave.read_own", "leave.update_own", "leave.write", "legal.create_own", "legal.read", "legal.read_own", "legal.update_own", "legal.write", "settings.read", "settings.write", "shifts.create_own", "shifts.read", "shifts.read_own", "shifts.update_own", "shifts.write", "signatures.create_own", "signatures.read", "signatures.read_own", "signatures.update_own", "signatures.write", "tenant.billing", "tenant.read", "tenant.write", "work_centers.read", "work_centers.write"]	2026-05-25 19:03:03.397413	2026-05-25 19:03:03.397429
b58c39c5-473e-4dd2-9d8c-1d6af0094d5c	cf26f84d-f21f-4138-a024-e6ce33797ffd	Inspector de Trabajo	Solo lectura en todos los módulos	t	["breaks.read", "breaks.read_own", "clock_ins.read", "clock_ins.read_own", "companies.read", "departments.read", "documents.read", "documents.read_own", "employees.read", "employees.read_own", "groups.read", "leave.approve", "leave.read", "leave.read_own", "legal.read", "legal.read_own", "settings.read", "shifts.read", "shifts.read_own", "signatures.read", "signatures.read_own", "tenant.read", "work_centers.read"]	2026-05-25 19:03:03.400592	2026-05-25 19:03:03.400606
70c7abf5-5e5b-4f3a-86c7-b75c1621dda6	951a449d-5f92-49c5-aec3-b3de06c44bcf	Empleados con panel	Consulta de fichajes y vacaciones propias	t	["breaks.create_own", "breaks.read_own", "clock_ins.create_own", "clock_ins.read_own", "documents.read_own", "leave.create_own", "leave.read_own", "leave.update_own", "legal.read", "legal.read_own", "legal.update_own", "signatures.read_own"]	2026-05-25 20:02:55.92785	2026-05-25 20:02:55.927865
47192355-d823-4fd5-a439-2f5d617540b2	951a449d-5f92-49c5-aec3-b3de06c44bcf	Inspector de Trabajo	Solo lectura en todos los módulos	t	["breaks.read", "breaks.read_own", "clock_ins.read", "clock_ins.read_own", "companies.read", "departments.read", "documents.read", "documents.read_own", "employees.read", "employees.read_own", "groups.read", "leave.approve", "leave.read", "leave.read_own", "legal.read", "legal.read_own", "settings.read", "shifts.read", "shifts.read_own", "signatures.read", "signatures.read_own", "tenant.read", "work_centers.read"]	2026-05-25 20:02:55.928565	2026-05-25 20:02:55.928579
12173caf-aacc-4871-83dd-a9f498f61d03	cf26f84d-f21f-4138-a024-e6ce33797ffd	Responsables	Gestión de equipos: empleados, fichajes, vacaciones y turnos en su ámbito	t	["breaks.create_own", "breaks.read", "breaks.update_own", "clock_ins.create_own", "clock_ins.read", "clock_ins.update_own", "companies.read", "departments.read", "documents.bulk", "documents.read", "documents.write", "employees.read", "employees.write", "groups.read", "leave.approve", "leave.read", "leave.write", "legal.read", "legal.write", "shifts.read", "shifts.write", "signatures.read", "signatures.write", "tenant.read", "work_centers.read"]	2026-05-25 19:03:03.399122	2026-05-25 19:03:03.399137
6735b40b-a4ed-4336-8776-b65f763a3531	951a449d-5f92-49c5-aec3-b3de06c44bcf	Administradores de cuenta	Control total del tenant: empresas, centros, departamentos y configuración	t	["breaks.create_own", "breaks.read", "breaks.read_own", "breaks.update_own", "breaks.write", "clock_ins.create_own", "clock_ins.read", "clock_ins.read_own", "clock_ins.update_own", "clock_ins.write", "companies.read", "companies.write", "departments.read", "departments.write", "documents.bulk", "documents.create_own", "documents.read", "documents.read_own", "documents.update_own", "documents.write", "employees.create_own", "employees.delete", "employees.read", "employees.read_own", "employees.update_own", "employees.write", "gowa.manage", "groups.read", "groups.write", "leave.approve", "leave.create_own", "leave.read", "leave.read_own", "leave.update_own", "leave.write", "legal.create_own", "legal.read", "legal.read_own", "legal.update_own", "legal.write", "settings.read", "settings.write", "shifts.create_own", "shifts.read", "shifts.read_own", "shifts.update_own", "shifts.write", "signatures.create_own", "signatures.read", "signatures.read_own", "signatures.update_own", "signatures.write", "tenant.billing", "tenant.read", "tenant.write", "work_centers.read", "work_centers.write"]	2026-05-25 20:02:55.925569	2026-05-25 20:02:55.925584
4cd88a84-e0de-4fde-a559-dec3836a46be	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	Empleados con panel	Consulta de fichajes y vacaciones propias	t	["breaks.create_own", "breaks.read_own", "clock_ins.create_own", "clock_ins.read_own", "documents.read_own", "leave.create_own", "leave.read_own", "leave.update_own", "legal.read", "legal.read_own", "legal.update_own", "signatures.read_own"]	2026-06-07 16:55:41.581427	2026-06-07 16:55:41.58144
3cb58d8f-ff27-4171-9b79-d603e110af72	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	Inspector de Trabajo	Solo lectura en todos los módulos	t	["breaks.read", "breaks.read_own", "clock_ins.read", "clock_ins.read_own", "companies.read", "departments.read", "documents.read", "documents.read_own", "employees.read", "employees.read_own", "groups.read", "leave.approve", "leave.read", "leave.read_own", "legal.read", "legal.read_own", "settings.read", "shifts.read", "shifts.read_own", "signatures.read", "signatures.read_own", "tenant.read", "work_centers.read"]	2026-06-07 16:55:41.582138	2026-06-07 16:55:41.582153
819b1856-3f23-4e88-9783-83f0fb7f60b6	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	Administradores de cuenta	Control total del tenant: empresas, centros, departamentos y configuración	t	["breaks.create_own", "breaks.read", "breaks.read_own", "breaks.update_own", "breaks.write", "clock_ins.create_own", "clock_ins.read", "clock_ins.read_own", "clock_ins.update_own", "clock_ins.write", "companies.read", "companies.write", "departments.read", "departments.write", "documents.bulk", "documents.create_own", "documents.read", "documents.read_own", "documents.update_own", "documents.write", "employees.create_own", "employees.delete", "employees.read", "employees.read_own", "employees.update_own", "employees.write", "gowa.manage", "groups.read", "groups.write", "leave.approve", "leave.create_own", "leave.read", "leave.read_own", "leave.update_own", "leave.write", "legal.create_own", "legal.read", "legal.read_own", "legal.update_own", "legal.write", "settings.read", "settings.write", "shifts.create_own", "shifts.read", "shifts.read_own", "shifts.update_own", "shifts.write", "signatures.create_own", "signatures.read", "signatures.read_own", "signatures.update_own", "signatures.write", "tenant.billing", "tenant.read", "tenant.write", "work_centers.read", "work_centers.write"]	2026-06-07 16:55:41.57861	2026-06-07 16:55:41.578625
77904f25-41ec-4050-bb4b-5c5b0b6babf4	951a449d-5f92-49c5-aec3-b3de06c44bcf	Responsables	Gestión de equipos: empleados, fichajes, vacaciones y turnos en su ámbito	t	["breaks.create_own", "breaks.read", "breaks.update_own", "clock_ins.create_own", "clock_ins.read", "clock_ins.update_own", "companies.read", "departments.read", "documents.bulk", "documents.read", "documents.write", "employees.read", "employees.write", "groups.read", "leave.approve", "leave.read", "leave.write", "legal.read", "legal.write", "shifts.read", "shifts.write", "signatures.read", "signatures.write", "tenant.read", "work_centers.read"]	2026-05-25 20:02:55.927077	2026-05-25 20:02:55.927092
f8873d0b-8d96-4288-8b01-59eb597ebe00	bdd57572-5518-48c0-9e27-b9f2c23591de	Administradores de cuenta	Control total del tenant: empresas, centros, departamentos y configuración	t	["breaks.create_own", "breaks.read", "breaks.read_own", "breaks.update_own", "breaks.write", "clock_ins.create_own", "clock_ins.read", "clock_ins.read_own", "clock_ins.update_own", "clock_ins.write", "companies.read", "companies.write", "departments.read", "departments.write", "documents.bulk", "documents.create_own", "documents.read", "documents.read_own", "documents.update_own", "documents.write", "employees.create_own", "employees.delete", "employees.read", "employees.read_own", "employees.update_own", "employees.write", "gowa.manage", "groups.read", "groups.write", "leave.approve", "leave.create_own", "leave.read", "leave.read_own", "leave.update_own", "leave.write", "legal.create_own", "legal.read", "legal.read_own", "legal.update_own", "legal.write", "settings.read", "settings.write", "shifts.create_own", "shifts.read", "shifts.read_own", "shifts.update_own", "shifts.write", "signatures.create_own", "signatures.read", "signatures.read_own", "signatures.update_own", "signatures.write", "tenant.billing", "tenant.read", "tenant.write", "work_centers.read", "work_centers.write"]	2026-06-14 17:37:01.255369	2026-06-14 17:37:01.255407
4d4dabfe-67f6-4228-b32c-0b68036c52d3	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	Administradores de cuenta	Control total del tenant: empresas, centros, departamentos y configuración	t	["breaks.create_own", "breaks.read", "breaks.read_own", "breaks.update_own", "breaks.write", "clock_ins.create_own", "clock_ins.read", "clock_ins.read_own", "clock_ins.update_own", "clock_ins.write", "companies.read", "companies.write", "departments.read", "departments.write", "documents.bulk", "documents.create_own", "documents.read", "documents.read_own", "documents.update_own", "documents.write", "employees.create_own", "employees.delete", "employees.read", "employees.read_own", "employees.update_own", "employees.write", "gowa.manage", "groups.read", "groups.write", "leave.approve", "leave.create_own", "leave.read", "leave.read_own", "leave.update_own", "leave.write", "legal.create_own", "legal.read", "legal.read_own", "legal.update_own", "legal.write", "settings.read", "settings.write", "shifts.create_own", "shifts.read", "shifts.read_own", "shifts.update_own", "shifts.write", "signatures.create_own", "signatures.read", "signatures.read_own", "signatures.update_own", "signatures.write", "tenant.billing", "tenant.read", "tenant.write", "work_centers.read", "work_centers.write"]	2026-06-14 17:45:13.469507	2026-06-14 17:45:13.469523
5979e73c-9bd3-4ee0-8c8e-e82695f0b4df	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	Responsables	Gestión de equipos: empleados, fichajes, vacaciones y turnos en su ámbito	t	["breaks.create_own", "breaks.read", "breaks.update_own", "clock_ins.create_own", "clock_ins.read", "clock_ins.update_own", "companies.read", "departments.read", "documents.bulk", "documents.read", "documents.write", "employees.read", "employees.write", "groups.read", "leave.approve", "leave.read", "leave.write", "legal.read", "legal.write", "shifts.read", "shifts.write", "signatures.read", "signatures.write", "tenant.read", "work_centers.read"]	2026-06-14 17:45:13.471348	2026-06-14 17:45:13.471364
554f8f89-687c-4add-bfbd-bfa575df8a19	bdd57572-5518-48c0-9e27-b9f2c23591de	Empleados con panel	Consulta de fichajes y vacaciones propias	t	["breaks.create_own", "breaks.read_own", "clock_ins.create_own", "clock_ins.read_own", "documents.read_own", "leave.create_own", "leave.read_own", "leave.update_own", "legal.read", "legal.read_own", "legal.update_own", "signatures.read_own"]	2026-06-14 17:37:01.259083	2026-06-14 17:37:01.259104
9547231f-332e-429d-aedb-b6d36f542884	bdd57572-5518-48c0-9e27-b9f2c23591de	Responsables	Gestión de equipos: empleados, fichajes, vacaciones y turnos en su ámbito	t	["breaks.create_own", "breaks.read", "breaks.update_own", "clock_ins.create_own", "clock_ins.read", "clock_ins.update_own", "companies.read", "departments.read", "documents.bulk", "documents.read", "documents.write", "employees.read", "employees.write", "groups.read", "leave.approve", "leave.read", "leave.write", "legal.read", "legal.write", "shifts.read", "shifts.write", "signatures.read", "signatures.write", "tenant.read", "work_centers.read"]	2026-06-14 17:37:01.258067	2026-06-14 17:37:01.258085
33508603-5217-4923-a04e-972bffbe48d9	bdd57572-5518-48c0-9e27-b9f2c23591de	Inspector de Trabajo	Solo lectura en todos los módulos	t	["breaks.read", "breaks.read_own", "clock_ins.read", "clock_ins.read_own", "companies.read", "departments.read", "documents.read", "documents.read_own", "employees.read", "employees.read_own", "groups.read", "leave.approve", "leave.read", "leave.read_own", "legal.read", "legal.read_own", "settings.read", "shifts.read", "shifts.read_own", "signatures.read", "signatures.read_own", "tenant.read", "work_centers.read"]	2026-06-14 17:37:01.260071	2026-06-14 17:37:01.260086
8843438d-4330-4585-9005-c917f5c87a3a	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	Empleados con panel	Consulta de fichajes y vacaciones propias	t	["breaks.create_own", "breaks.read_own", "clock_ins.create_own", "clock_ins.read_own", "documents.read_own", "leave.create_own", "leave.read_own", "leave.update_own", "legal.read", "legal.read_own", "legal.update_own", "signatures.read_own"]	2026-06-14 17:45:13.472082	2026-06-14 17:45:13.472097
e1c88780-da3b-4b4f-ab24-53d3c0fee7a1	deed7ddf-0b0a-4a8b-8c4f-45d2b3ab0cd8	Inspector de Trabajo	Solo lectura en todos los módulos	t	["breaks.read", "breaks.read_own", "clock_ins.read", "clock_ins.read_own", "companies.read", "departments.read", "documents.read", "documents.read_own", "employees.read", "employees.read_own", "groups.read", "leave.approve", "leave.read", "leave.read_own", "legal.read", "legal.read_own", "settings.read", "shifts.read", "shifts.read_own", "signatures.read", "signatures.read_own", "tenant.read", "work_centers.read"]	2026-06-14 17:45:13.472877	2026-06-14 17:45:13.472891
d867fe5d-cfbd-4f1e-984a-e6f438597598	cbbf551f-87c4-47f4-aa8b-cd20e7036a61	Responsables	Gestión de equipos: empleados, fichajes, vacaciones y turnos en su ámbito	t	["breaks.create_own", "breaks.read", "breaks.update_own", "clock_ins.create_own", "clock_ins.read", "clock_ins.update_own", "companies.read", "departments.read", "documents.bulk", "documents.read", "documents.write", "employees.read", "employees.write", "groups.read", "leave.approve", "leave.read", "leave.write", "legal.read", "legal.write", "shifts.read", "shifts.write", "signatures.read", "signatures.write", "tenant.read", "work_centers.read"]	2026-06-07 16:55:41.580679	2026-06-07 16:55:41.580694
\.


--
-- Data for Name: webhook_deliveries; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.webhook_deliveries (id, webhook_id, event_type, payload, status, response_status, response_body, attempts, created_at, delivered_at) FROM stdin;
\.


--
-- Data for Name: webhook_endpoints; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.webhook_endpoints (id, tenant_id, url, description, events, secret, is_active, created_at, last_triggered_at, failure_count) FROM stdin;
\.


--
-- Data for Name: whatsapp_dedup; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.whatsapp_dedup (wa_msg_id, created_at) FROM stdin;
34633859349:2AE45E9D0895F05E3CFF	2026-06-19 19:56:14.794761
34633859349:2A90FC2FE10A274F0214	2026-06-19 19:56:20.952071
\.


--
-- Data for Name: work_breaks; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.work_breaks (id, employee_id, record_type, recorded_at, source, notes, whatsapp_message_id, clock_in_id) FROM stdin;
f091c69b-9ce3-4442-8cbd-b89868bb49a1	f41acab0-d7a1-4441-942b-69664ceb9d3b	INICIO	2026-06-08 13:25:00	incident_action	\N	\N	a7b04d05-f9a4-4e10-b72e-9c22b84a7552
178c4056-c884-4319-b4d3-2455a67f5893	f41acab0-d7a1-4441-942b-69664ceb9d3b	INICIO	2026-06-11 09:59:32.29671	whatsapp	\N	3EB0422B8F060121E6BC61	3b53a451-cbfb-4e35-a637-2b151961e2d7
d91c9a22-aac5-45d2-a704-db3b1b1ec166	f41acab0-d7a1-4441-942b-69664ceb9d3b	FIN	2026-06-11 11:44:01.028191	whatsapp	\N	3EB093B716DA1EDDCF7FD0	3b53a451-cbfb-4e35-a637-2b151961e2d7
\.


--
-- Data for Name: work_centers; Type: TABLE DATA; Schema: public; Owner: hrm
--

COPY public.work_centers (id, company_id, name, code, address, city, is_active, created_at) FROM stdin;
155b210a-0a96-4203-bfb2-48ce0ef491df	f13fda9a-7d23-4597-86e9-2bcfadc2c677	Centro principal	CENTRO-01	\N	\N	t	2026-05-25 19:03:03.383518
f62ff184-1e70-4827-b5ea-48762c5cac3f	ec0da4d5-072b-4ede-85d3-439c47fc7e44	Centro principal	CENTRO-01	\N	\N	t	2026-05-25 20:02:55.914689
c96ce44c-4fd6-4cdc-bbe6-da31bd2d1145	bb7211f4-1102-4865-a44c-cebcf8f075c8	Centro principal	CENTRO-01	\N	\N	t	2026-06-07 16:55:41.566856
0ca67aca-9ce7-418d-91a1-d9d031b62ccd	bb7211f4-1102-4865-a44c-cebcf8f075c8	OFICINA	CEN-001	\N	\N	t	2026-06-12 11:32:21.893637
9e76d734-8db1-4d2c-a4ee-b45885874e87	376289a5-f76d-42e5-a07e-d266ec828caa	Centro principal	C-376289A5	\N	\N	t	2026-06-12 14:33:08.666073
2eedf1c4-ff1b-4900-8765-7d7a58437d32	35694ea1-39a1-4a90-99c9-2616c4b1adf1	Centro principal	C-35694EA1	\N	\N	t	2026-06-12 14:33:08.674133
d29f83ef-5aba-43a2-90a8-2b8465d08c12	4553c7c5-ec1f-4273-8053-4498eccd7f63	Centro principal	CENTRO-01	\N	\N	t	2026-06-14 17:37:01.236984
17c2163b-2823-4aab-b2d3-71eecf1e77e0	78fe1d81-289a-44c5-9897-eb3a2689ae56	Centro principal	CENTRO-01	\N	\N	t	2026-06-14 17:45:13.453992
\.


--
-- Name: ai_actions ai_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_actions
    ADD CONSTRAINT ai_actions_pkey PRIMARY KEY (id);


--
-- Name: ai_conversation_rules ai_conversation_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_conversation_rules
    ADD CONSTRAINT ai_conversation_rules_pkey PRIMARY KEY (id);


--
-- Name: ai_profile_actions ai_profile_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_profile_actions
    ADD CONSTRAINT ai_profile_actions_pkey PRIMARY KEY (id);


--
-- Name: ai_usage_records ai_usage_records_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_usage_records
    ADD CONSTRAINT ai_usage_records_pkey PRIMARY KEY (id);


--
-- Name: ai_whatsapp_messages ai_whatsapp_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_whatsapp_messages
    ADD CONSTRAINT ai_whatsapp_messages_pkey PRIMARY KEY (id);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: billing_methods billing_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.billing_methods
    ADD CONSTRAINT billing_methods_pkey PRIMARY KEY (id);


--
-- Name: clock_ins clock_ins_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.clock_ins
    ADD CONSTRAINT clock_ins_pkey PRIMARY KEY (id);


--
-- Name: clock_pending_fichajes clock_pending_fichajes_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.clock_pending_fichajes
    ADD CONSTRAINT clock_pending_fichajes_pkey PRIMARY KEY (employee_id);


--
-- Name: clock_settings clock_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.clock_settings
    ADD CONSTRAINT clock_settings_pkey PRIMARY KEY (tenant_id);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: discounts discounts_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.discounts
    ADD CONSTRAINT discounts_pkey PRIMARY KEY (id);


--
-- Name: document_deliveries document_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_deliveries
    ADD CONSTRAINT document_deliveries_pkey PRIMARY KEY (id);


--
-- Name: document_delivery_tags document_delivery_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_delivery_tags
    ADD CONSTRAINT document_delivery_tags_pkey PRIMARY KEY (id);


--
-- Name: document_expiry_notification_logs document_expiry_notification_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_expiry_notification_logs
    ADD CONSTRAINT document_expiry_notification_logs_pkey PRIMARY KEY (id);


--
-- Name: document_notification_settings document_notification_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_notification_settings
    ADD CONSTRAINT document_notification_settings_pkey PRIMARY KEY (tenant_id);


--
-- Name: document_tags document_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_tags
    ADD CONSTRAINT document_tags_pkey PRIMARY KEY (id);


--
-- Name: document_types document_types_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT document_types_pkey PRIMARY KEY (id);


--
-- Name: employee_groups employee_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_groups
    ADD CONSTRAINT employee_groups_pkey PRIMARY KEY (id);


--
-- Name: employee_inbound_documents employee_inbound_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_inbound_documents
    ADD CONSTRAINT employee_inbound_documents_pkey PRIMARY KEY (id);


--
-- Name: employee_leave_balances employee_leave_balances_employee_id_leave_type_id_key; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_leave_balances
    ADD CONSTRAINT employee_leave_balances_employee_id_leave_type_id_key UNIQUE (employee_id, leave_type_id);


--
-- Name: employee_leave_balances employee_leave_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_leave_balances
    ADD CONSTRAINT employee_leave_balances_pkey PRIMARY KEY (id);


--
-- Name: employees employees_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_pkey PRIMARY KEY (id);


--
-- Name: group_templates group_templates_name_key; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.group_templates
    ADD CONSTRAINT group_templates_name_key UNIQUE (name);


--
-- Name: group_templates group_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.group_templates
    ADD CONSTRAINT group_templates_pkey PRIMARY KEY (id);


--
-- Name: inbound_pending_uploads inbound_pending_uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.inbound_pending_uploads
    ADD CONSTRAINT inbound_pending_uploads_pkey PRIMARY KEY (employee_id);


--
-- Name: incident_auto_rules incident_auto_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incident_auto_rules
    ADD CONSTRAINT incident_auto_rules_pkey PRIMARY KEY (tenant_id);


--
-- Name: incident_notes incident_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incident_notes
    ADD CONSTRAINT incident_notes_pkey PRIMARY KEY (id);


--
-- Name: incidents incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: leave_requests leave_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_pkey PRIMARY KEY (id);


--
-- Name: leave_types leave_types_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.leave_types
    ADD CONSTRAINT leave_types_pkey PRIMARY KEY (id);


--
-- Name: legal_acceptances legal_acceptances_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_acceptances
    ADD CONSTRAINT legal_acceptances_pkey PRIMARY KEY (id);


--
-- Name: legal_documents legal_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_documents
    ADD CONSTRAINT legal_documents_pkey PRIMARY KEY (id);


--
-- Name: legal_tokens legal_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_tokens
    ADD CONSTRAINT legal_tokens_pkey PRIMARY KEY (id);


--
-- Name: ls_payments ls_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ls_payments
    ADD CONSTRAINT ls_payments_pkey PRIMARY KEY (id);


--
-- Name: mail_logs mail_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.mail_logs
    ADD CONSTRAINT mail_logs_pkey PRIMARY KEY (id);


--
-- Name: notification_preferences notification_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.notification_preferences
    ADD CONSTRAINT notification_preferences_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: pending_signups pending_signups_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.pending_signups
    ADD CONSTRAINT pending_signups_pkey PRIMARY KEY (id);


--
-- Name: platform_policies platform_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.platform_policies
    ADD CONSTRAINT platform_policies_pkey PRIMARY KEY (id);


--
-- Name: platform_settings platform_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.platform_settings
    ADD CONSTRAINT platform_settings_pkey PRIMARY KEY (id);


--
-- Name: platform_users platform_users_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.platform_users
    ADD CONSTRAINT platform_users_pkey PRIMARY KEY (id);


--
-- Name: pricing_plans pricing_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.pricing_plans
    ADD CONSTRAINT pricing_plans_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: shift_assignments shift_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.shift_assignments
    ADD CONSTRAINT shift_assignments_pkey PRIMARY KEY (id);


--
-- Name: shift_configurations shift_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.shift_configurations
    ADD CONSTRAINT shift_configurations_pkey PRIMARY KEY (id);


--
-- Name: signature_envelopes signature_envelopes_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_envelopes
    ADD CONSTRAINT signature_envelopes_pkey PRIMARY KEY (id);


--
-- Name: signature_events signature_events_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_events
    ADD CONSTRAINT signature_events_pkey PRIMARY KEY (id);


--
-- Name: signature_notifications signature_notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_notifications
    ADD CONSTRAINT signature_notifications_pkey PRIMARY KEY (id);


--
-- Name: signature_otps signature_otps_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_otps
    ADD CONSTRAINT signature_otps_pkey PRIMARY KEY (id);


--
-- Name: signature_signers signature_signers_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_signers
    ADD CONSTRAINT signature_signers_pkey PRIMARY KEY (id);


--
-- Name: stripe_payments stripe_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.stripe_payments
    ADD CONSTRAINT stripe_payments_pkey PRIMARY KEY (id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: ai_profile_actions uq_ai_profile_action; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_profile_actions
    ADD CONSTRAINT uq_ai_profile_action UNIQUE (action_id, profile_key);


--
-- Name: departments uq_department_code_wc; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT uq_department_code_wc UNIQUE (work_center_id, code);


--
-- Name: document_expiry_notification_logs uq_doc_expiry_notif; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_expiry_notification_logs
    ADD CONSTRAINT uq_doc_expiry_notif UNIQUE (document_delivery_id, days_before, channel, recipient);


--
-- Name: document_delivery_tags uq_document_delivery_tag; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_delivery_tags
    ADD CONSTRAINT uq_document_delivery_tag UNIQUE (document_delivery_id, tag_id);


--
-- Name: document_tags uq_document_tag_tenant_name; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_tags
    ADD CONSTRAINT uq_document_tag_tenant_name UNIQUE (tenant_id, name);


--
-- Name: document_types uq_document_type_tenant_code; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT uq_document_type_tenant_code UNIQUE (tenant_id, code);


--
-- Name: employees uq_employee_code_company; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT uq_employee_code_company UNIQUE (company_id, employee_code);


--
-- Name: employee_groups uq_employee_group; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_groups
    ADD CONSTRAINT uq_employee_group UNIQUE (employee_id, group_id);


--
-- Name: employees uq_employee_id_document_company; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT uq_employee_id_document_company UNIQUE (company_id, id_document);


--
-- Name: employees uq_employee_phone_company; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT uq_employee_phone_company UNIQUE (company_id, phone);


--
-- Name: user_groups uq_group_name_tenant; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT uq_group_name_tenant UNIQUE (tenant_id, name);


--
-- Name: legal_acceptances uq_legal_acceptance_employee_doc; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_acceptances
    ADD CONSTRAINT uq_legal_acceptance_employee_doc UNIQUE (employee_id, legal_document_id);


--
-- Name: legal_documents uq_legal_doc_tenant_code; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_documents
    ADD CONSTRAINT uq_legal_doc_tenant_code UNIQUE (tenant_id, code);


--
-- Name: signature_signers uq_signer_envelope_order; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_signers
    ADD CONSTRAINT uq_signer_envelope_order UNIQUE (envelope_id, sign_order);


--
-- Name: work_centers uq_work_center_code_company; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.work_centers
    ADD CONSTRAINT uq_work_center_code_company UNIQUE (company_id, code);


--
-- Name: user_groups user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_pkey PRIMARY KEY (id);


--
-- Name: webhook_deliveries webhook_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.webhook_deliveries
    ADD CONSTRAINT webhook_deliveries_pkey PRIMARY KEY (id);


--
-- Name: webhook_endpoints webhook_endpoints_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.webhook_endpoints
    ADD CONSTRAINT webhook_endpoints_pkey PRIMARY KEY (id);


--
-- Name: whatsapp_dedup whatsapp_dedup_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.whatsapp_dedup
    ADD CONSTRAINT whatsapp_dedup_pkey PRIMARY KEY (wa_msg_id);


--
-- Name: work_breaks work_breaks_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.work_breaks
    ADD CONSTRAINT work_breaks_pkey PRIMARY KEY (id);


--
-- Name: work_centers work_centers_pkey; Type: CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.work_centers
    ADD CONSTRAINT work_centers_pkey PRIMARY KEY (id);


--
-- Name: idx_invoices_ls_payment; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_invoices_ls_payment ON public.invoices USING btree (ls_payment_id);


--
-- Name: idx_invoices_number; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_invoices_number ON public.invoices USING btree (number);


--
-- Name: idx_invoices_stripe_payment; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_invoices_stripe_payment ON public.invoices USING btree (stripe_payment_id);


--
-- Name: idx_invoices_tenant; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_invoices_tenant ON public.invoices USING btree (tenant_id);


--
-- Name: idx_ls_payments_invoice; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_ls_payments_invoice ON public.ls_payments USING btree (ls_invoice_id);


--
-- Name: idx_ls_payments_order; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_ls_payments_order ON public.ls_payments USING btree (ls_order_id);


--
-- Name: idx_ls_payments_sub; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_ls_payments_sub ON public.ls_payments USING btree (ls_subscription_id);


--
-- Name: idx_ls_payments_tenant; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_ls_payments_tenant ON public.ls_payments USING btree (tenant_id);


--
-- Name: idx_subscriptions_ls_sub; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_subscriptions_ls_sub ON public.subscriptions USING btree (ls_subscription_id);


--
-- Name: idx_tenants_ls_customer; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX idx_tenants_ls_customer ON public.tenants USING btree (ls_customer_id);


--
-- Name: ix_ai_actions_category; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_actions_category ON public.ai_actions USING btree (category);


--
-- Name: ix_ai_actions_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE UNIQUE INDEX ix_ai_actions_code ON public.ai_actions USING btree (code);


--
-- Name: ix_ai_conversation_rules_priority; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_conversation_rules_priority ON public.ai_conversation_rules USING btree (priority);


--
-- Name: ix_ai_profile_actions_action_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_profile_actions_action_id ON public.ai_profile_actions USING btree (action_id);


--
-- Name: ix_ai_profile_actions_profile_key; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_profile_actions_profile_key ON public.ai_profile_actions USING btree (profile_key);


--
-- Name: ix_ai_usage_records_action_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_usage_records_action_code ON public.ai_usage_records USING btree (action_code);


--
-- Name: ix_ai_usage_records_created_at; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_usage_records_created_at ON public.ai_usage_records USING btree (created_at);


--
-- Name: ix_ai_usage_records_profile_key; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_usage_records_profile_key ON public.ai_usage_records USING btree (profile_key);


--
-- Name: ix_ai_usage_records_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_usage_records_tenant_id ON public.ai_usage_records USING btree (tenant_id);


--
-- Name: ix_ai_whatsapp_messages_created_at; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_whatsapp_messages_created_at ON public.ai_whatsapp_messages USING btree (created_at);


--
-- Name: ix_ai_whatsapp_messages_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_whatsapp_messages_employee_id ON public.ai_whatsapp_messages USING btree (employee_id);


--
-- Name: ix_ai_whatsapp_messages_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ai_whatsapp_messages_tenant_id ON public.ai_whatsapp_messages USING btree (tenant_id);


--
-- Name: ix_api_keys_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_api_keys_tenant_id ON public.api_keys USING btree (tenant_id);


--
-- Name: ix_billing_methods_company_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_billing_methods_company_id ON public.billing_methods USING btree (company_id);


--
-- Name: ix_billing_methods_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_billing_methods_tenant_id ON public.billing_methods USING btree (tenant_id);


--
-- Name: ix_clock_ins_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_clock_ins_employee_id ON public.clock_ins USING btree (employee_id);


--
-- Name: ix_clock_ins_project_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_clock_ins_project_id ON public.clock_ins USING btree (project_id);


--
-- Name: ix_companies_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_companies_tenant_id ON public.companies USING btree (tenant_id);


--
-- Name: ix_departments_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_departments_code ON public.departments USING btree (code);


--
-- Name: ix_departments_work_center_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_departments_work_center_id ON public.departments USING btree (work_center_id);


--
-- Name: ix_discounts_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE UNIQUE INDEX ix_discounts_code ON public.discounts USING btree (code);


--
-- Name: ix_document_deliveries_company_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_deliveries_company_id ON public.document_deliveries USING btree (company_id);


--
-- Name: ix_document_deliveries_document_type_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_deliveries_document_type_id ON public.document_deliveries USING btree (document_type_id);


--
-- Name: ix_document_deliveries_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_deliveries_employee_id ON public.document_deliveries USING btree (employee_id);


--
-- Name: ix_document_deliveries_expires_at; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_deliveries_expires_at ON public.document_deliveries USING btree (expires_at);


--
-- Name: ix_document_deliveries_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_deliveries_tenant_id ON public.document_deliveries USING btree (tenant_id);


--
-- Name: ix_document_delivery_tags_document_delivery_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_delivery_tags_document_delivery_id ON public.document_delivery_tags USING btree (document_delivery_id);


--
-- Name: ix_document_delivery_tags_tag_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_delivery_tags_tag_id ON public.document_delivery_tags USING btree (tag_id);


--
-- Name: ix_document_expiry_notification_logs_document_delivery_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_expiry_notification_logs_document_delivery_id ON public.document_expiry_notification_logs USING btree (document_delivery_id);


--
-- Name: ix_document_expiry_notification_logs_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_expiry_notification_logs_tenant_id ON public.document_expiry_notification_logs USING btree (tenant_id);


--
-- Name: ix_document_tags_name; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_tags_name ON public.document_tags USING btree (name);


--
-- Name: ix_document_tags_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_tags_tenant_id ON public.document_tags USING btree (tenant_id);


--
-- Name: ix_document_types_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_types_code ON public.document_types USING btree (code);


--
-- Name: ix_document_types_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_document_types_tenant_id ON public.document_types USING btree (tenant_id);


--
-- Name: ix_employee_groups_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employee_groups_employee_id ON public.employee_groups USING btree (employee_id);


--
-- Name: ix_employee_groups_group_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employee_groups_group_id ON public.employee_groups USING btree (group_id);


--
-- Name: ix_employee_inbound_documents_document_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employee_inbound_documents_document_code ON public.employee_inbound_documents USING btree (document_code);


--
-- Name: ix_employee_inbound_documents_document_delivery_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employee_inbound_documents_document_delivery_id ON public.employee_inbound_documents USING btree (document_delivery_id);


--
-- Name: ix_employee_inbound_documents_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employee_inbound_documents_employee_id ON public.employee_inbound_documents USING btree (employee_id);


--
-- Name: ix_employee_inbound_documents_signature_envelope_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employee_inbound_documents_signature_envelope_id ON public.employee_inbound_documents USING btree (signature_envelope_id);


--
-- Name: ix_employee_leave_balances_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employee_leave_balances_employee_id ON public.employee_leave_balances USING btree (employee_id);


--
-- Name: ix_employee_leave_balances_leave_type_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employee_leave_balances_leave_type_id ON public.employee_leave_balances USING btree (leave_type_id);


--
-- Name: ix_employees_avatar_delivery_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employees_avatar_delivery_id ON public.employees USING btree (avatar_delivery_id);


--
-- Name: ix_employees_company_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employees_company_id ON public.employees USING btree (company_id);


--
-- Name: ix_employees_department_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employees_department_id ON public.employees USING btree (department_id);


--
-- Name: ix_employees_id_document; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employees_id_document ON public.employees USING btree (id_document);


--
-- Name: ix_employees_shift_configuration_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_employees_shift_configuration_id ON public.employees USING btree (shift_configuration_id);


--
-- Name: ix_incident_notes_incident_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_incident_notes_incident_id ON public.incident_notes USING btree (incident_id);


--
-- Name: ix_incidents_break_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_incidents_break_id ON public.incidents USING btree (break_id);


--
-- Name: ix_incidents_clock_in_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_incidents_clock_in_id ON public.incidents USING btree (clock_in_id);


--
-- Name: ix_incidents_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_incidents_employee_id ON public.incidents USING btree (employee_id);


--
-- Name: ix_incidents_leave_request_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_incidents_leave_request_id ON public.incidents USING btree (leave_request_id);


--
-- Name: ix_incidents_managed; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_incidents_managed ON public.incidents USING btree (managed);


--
-- Name: ix_incidents_public_token; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_incidents_public_token ON public.incidents USING btree (public_token);


--
-- Name: ix_incidents_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_incidents_tenant_id ON public.incidents USING btree (tenant_id);


--
-- Name: ix_invoices_number; Type: INDEX; Schema: public; Owner: hrm
--

CREATE UNIQUE INDEX ix_invoices_number ON public.invoices USING btree (number);


--
-- Name: ix_invoices_stripe_payment_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_invoices_stripe_payment_id ON public.invoices USING btree (stripe_payment_id);


--
-- Name: ix_invoices_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_invoices_tenant_id ON public.invoices USING btree (tenant_id);


--
-- Name: ix_leave_requests_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_leave_requests_employee_id ON public.leave_requests USING btree (employee_id);


--
-- Name: ix_leave_types_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_leave_types_tenant_id ON public.leave_types USING btree (tenant_id);


--
-- Name: ix_legal_acceptances_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_legal_acceptances_employee_id ON public.legal_acceptances USING btree (employee_id);


--
-- Name: ix_legal_acceptances_legal_document_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_legal_acceptances_legal_document_id ON public.legal_acceptances USING btree (legal_document_id);


--
-- Name: ix_legal_documents_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_legal_documents_code ON public.legal_documents USING btree (code);


--
-- Name: ix_legal_documents_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_legal_documents_tenant_id ON public.legal_documents USING btree (tenant_id);


--
-- Name: ix_legal_tokens_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_legal_tokens_employee_id ON public.legal_tokens USING btree (employee_id);


--
-- Name: ix_legal_tokens_token; Type: INDEX; Schema: public; Owner: hrm
--

CREATE UNIQUE INDEX ix_legal_tokens_token ON public.legal_tokens USING btree (token);


--
-- Name: ix_ls_payments_ls_invoice_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ls_payments_ls_invoice_id ON public.ls_payments USING btree (ls_invoice_id);


--
-- Name: ix_ls_payments_ls_order_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ls_payments_ls_order_id ON public.ls_payments USING btree (ls_order_id);


--
-- Name: ix_ls_payments_ls_subscription_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ls_payments_ls_subscription_id ON public.ls_payments USING btree (ls_subscription_id);


--
-- Name: ix_ls_payments_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_ls_payments_tenant_id ON public.ls_payments USING btree (tenant_id);


--
-- Name: ix_mail_logs_created_at; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_mail_logs_created_at ON public.mail_logs USING btree (created_at);


--
-- Name: ix_mail_logs_envelope_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_mail_logs_envelope_id ON public.mail_logs USING btree (envelope_id);


--
-- Name: ix_mail_logs_event_type; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_mail_logs_event_type ON public.mail_logs USING btree (event_type);


--
-- Name: ix_mail_logs_success; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_mail_logs_success ON public.mail_logs USING btree (success);


--
-- Name: ix_mail_logs_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_mail_logs_tenant_id ON public.mail_logs USING btree (tenant_id);


--
-- Name: ix_mail_logs_to_address; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_mail_logs_to_address ON public.mail_logs USING btree (to_address);


--
-- Name: ix_notification_preferences_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_notification_preferences_employee_id ON public.notification_preferences USING btree (employee_id);


--
-- Name: ix_notifications_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_notifications_employee_id ON public.notifications USING btree (employee_id);


--
-- Name: ix_notifications_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_notifications_tenant_id ON public.notifications USING btree (tenant_id);


--
-- Name: ix_password_reset_tokens_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_password_reset_tokens_employee_id ON public.password_reset_tokens USING btree (employee_id);


--
-- Name: ix_password_reset_tokens_token; Type: INDEX; Schema: public; Owner: hrm
--

CREATE UNIQUE INDEX ix_password_reset_tokens_token ON public.password_reset_tokens USING btree (token);


--
-- Name: ix_pending_signups_ls_subscription_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_pending_signups_ls_subscription_id ON public.pending_signups USING btree (ls_subscription_id);


--
-- Name: ix_platform_users_email; Type: INDEX; Schema: public; Owner: hrm
--

CREATE UNIQUE INDEX ix_platform_users_email ON public.platform_users USING btree (email);


--
-- Name: ix_pricing_plans_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE UNIQUE INDEX ix_pricing_plans_code ON public.pricing_plans USING btree (code);


--
-- Name: ix_projects_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_projects_code ON public.projects USING btree (code);


--
-- Name: ix_projects_company_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_projects_company_id ON public.projects USING btree (company_id);


--
-- Name: ix_shift_assignments_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_shift_assignments_employee_id ON public.shift_assignments USING btree (employee_id);


--
-- Name: ix_shift_assignments_shift_configuration_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_shift_assignments_shift_configuration_id ON public.shift_assignments USING btree (shift_configuration_id);


--
-- Name: ix_shift_configurations_company_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_shift_configurations_company_id ON public.shift_configurations USING btree (company_id);


--
-- Name: ix_signature_envelopes_document_delivery_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_envelopes_document_delivery_id ON public.signature_envelopes USING btree (document_delivery_id);


--
-- Name: ix_signature_envelopes_reference; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_envelopes_reference ON public.signature_envelopes USING btree (reference);


--
-- Name: ix_signature_envelopes_status; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_envelopes_status ON public.signature_envelopes USING btree (status);


--
-- Name: ix_signature_envelopes_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_envelopes_tenant_id ON public.signature_envelopes USING btree (tenant_id);


--
-- Name: ix_signature_events_envelope_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_events_envelope_id ON public.signature_events USING btree (envelope_id);


--
-- Name: ix_signature_events_event_type; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_events_event_type ON public.signature_events USING btree (event_type);


--
-- Name: ix_signature_notifications_envelope_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_notifications_envelope_id ON public.signature_notifications USING btree (envelope_id);


--
-- Name: ix_signature_otps_signer_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_otps_signer_id ON public.signature_otps USING btree (signer_id);


--
-- Name: ix_signature_signers_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_signers_employee_id ON public.signature_signers USING btree (employee_id);


--
-- Name: ix_signature_signers_envelope_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_signers_envelope_id ON public.signature_signers USING btree (envelope_id);


--
-- Name: ix_signature_signers_id_document; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_signers_id_document ON public.signature_signers USING btree (id_document);


--
-- Name: ix_signature_signers_token_hash; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_signature_signers_token_hash ON public.signature_signers USING btree (token_hash);


--
-- Name: ix_stripe_payments_stripe_invoice_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_stripe_payments_stripe_invoice_id ON public.stripe_payments USING btree (stripe_invoice_id);


--
-- Name: ix_stripe_payments_stripe_payment_intent_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_stripe_payments_stripe_payment_intent_id ON public.stripe_payments USING btree (stripe_payment_intent_id);


--
-- Name: ix_stripe_payments_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_stripe_payments_tenant_id ON public.stripe_payments USING btree (tenant_id);


--
-- Name: ix_subscriptions_company_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_subscriptions_company_id ON public.subscriptions USING btree (company_id);


--
-- Name: ix_subscriptions_stripe_subscription_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_subscriptions_stripe_subscription_id ON public.subscriptions USING btree (stripe_subscription_id);


--
-- Name: ix_subscriptions_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_subscriptions_tenant_id ON public.subscriptions USING btree (tenant_id);


--
-- Name: ix_tenants_slug; Type: INDEX; Schema: public; Owner: hrm
--

CREATE UNIQUE INDEX ix_tenants_slug ON public.tenants USING btree (slug);


--
-- Name: ix_tenants_stripe_customer_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_tenants_stripe_customer_id ON public.tenants USING btree (stripe_customer_id);


--
-- Name: ix_user_groups_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_user_groups_tenant_id ON public.user_groups USING btree (tenant_id);


--
-- Name: ix_webhook_deliveries_webhook_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_webhook_deliveries_webhook_id ON public.webhook_deliveries USING btree (webhook_id);


--
-- Name: ix_webhook_endpoints_tenant_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_webhook_endpoints_tenant_id ON public.webhook_endpoints USING btree (tenant_id);


--
-- Name: ix_whatsapp_dedup_created; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_whatsapp_dedup_created ON public.whatsapp_dedup USING btree (created_at);


--
-- Name: ix_work_breaks_clock_in_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_work_breaks_clock_in_id ON public.work_breaks USING btree (clock_in_id);


--
-- Name: ix_work_breaks_employee_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_work_breaks_employee_id ON public.work_breaks USING btree (employee_id);


--
-- Name: ix_work_centers_code; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_work_centers_code ON public.work_centers USING btree (code);


--
-- Name: ix_work_centers_company_id; Type: INDEX; Schema: public; Owner: hrm
--

CREATE INDEX ix_work_centers_company_id ON public.work_centers USING btree (company_id);


--
-- Name: ai_profile_actions ai_profile_actions_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_profile_actions
    ADD CONSTRAINT ai_profile_actions_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.ai_actions(id);


--
-- Name: ai_usage_records ai_usage_records_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_usage_records
    ADD CONSTRAINT ai_usage_records_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: ai_whatsapp_messages ai_whatsapp_messages_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_whatsapp_messages
    ADD CONSTRAINT ai_whatsapp_messages_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: ai_whatsapp_messages ai_whatsapp_messages_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ai_whatsapp_messages
    ADD CONSTRAINT ai_whatsapp_messages_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: api_keys api_keys_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.employees(id);


--
-- Name: api_keys api_keys_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: billing_methods billing_methods_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.billing_methods
    ADD CONSTRAINT billing_methods_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: billing_methods billing_methods_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.billing_methods
    ADD CONSTRAINT billing_methods_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: clock_ins clock_ins_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.clock_ins
    ADD CONSTRAINT clock_ins_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: clock_ins clock_ins_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.clock_ins
    ADD CONSTRAINT clock_ins_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: clock_pending_fichajes clock_pending_fichajes_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.clock_pending_fichajes
    ADD CONSTRAINT clock_pending_fichajes_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: clock_settings clock_settings_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.clock_settings
    ADD CONSTRAINT clock_settings_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: companies companies_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: departments departments_work_center_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_work_center_id_fkey FOREIGN KEY (work_center_id) REFERENCES public.work_centers(id);


--
-- Name: discounts discounts_pricing_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.discounts
    ADD CONSTRAINT discounts_pricing_plan_id_fkey FOREIGN KEY (pricing_plan_id) REFERENCES public.pricing_plans(id);


--
-- Name: document_deliveries document_deliveries_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_deliveries
    ADD CONSTRAINT document_deliveries_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: document_deliveries document_deliveries_document_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_deliveries
    ADD CONSTRAINT document_deliveries_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.document_types(id);


--
-- Name: document_deliveries document_deliveries_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_deliveries
    ADD CONSTRAINT document_deliveries_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: document_deliveries document_deliveries_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_deliveries
    ADD CONSTRAINT document_deliveries_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: document_delivery_tags document_delivery_tags_document_delivery_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_delivery_tags
    ADD CONSTRAINT document_delivery_tags_document_delivery_id_fkey FOREIGN KEY (document_delivery_id) REFERENCES public.document_deliveries(id);


--
-- Name: document_delivery_tags document_delivery_tags_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_delivery_tags
    ADD CONSTRAINT document_delivery_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.document_tags(id);


--
-- Name: document_expiry_notification_logs document_expiry_notification_logs_document_delivery_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_expiry_notification_logs
    ADD CONSTRAINT document_expiry_notification_logs_document_delivery_id_fkey FOREIGN KEY (document_delivery_id) REFERENCES public.document_deliveries(id);


--
-- Name: document_expiry_notification_logs document_expiry_notification_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_expiry_notification_logs
    ADD CONSTRAINT document_expiry_notification_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: document_notification_settings document_notification_settings_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_notification_settings
    ADD CONSTRAINT document_notification_settings_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: document_tags document_tags_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_tags
    ADD CONSTRAINT document_tags_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: document_types document_types_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT document_types_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: employee_groups employee_groups_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_groups
    ADD CONSTRAINT employee_groups_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: employee_groups employee_groups_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_groups
    ADD CONSTRAINT employee_groups_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.user_groups(id);


--
-- Name: employee_inbound_documents employee_inbound_documents_document_delivery_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_inbound_documents
    ADD CONSTRAINT employee_inbound_documents_document_delivery_id_fkey FOREIGN KEY (document_delivery_id) REFERENCES public.document_deliveries(id);


--
-- Name: employee_inbound_documents employee_inbound_documents_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_inbound_documents
    ADD CONSTRAINT employee_inbound_documents_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: employee_inbound_documents employee_inbound_documents_signature_envelope_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_inbound_documents
    ADD CONSTRAINT employee_inbound_documents_signature_envelope_id_fkey FOREIGN KEY (signature_envelope_id) REFERENCES public.signature_envelopes(id);


--
-- Name: employee_leave_balances employee_leave_balances_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_leave_balances
    ADD CONSTRAINT employee_leave_balances_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: employee_leave_balances employee_leave_balances_leave_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employee_leave_balances
    ADD CONSTRAINT employee_leave_balances_leave_type_id_fkey FOREIGN KEY (leave_type_id) REFERENCES public.leave_types(id);


--
-- Name: employees employees_avatar_delivery_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_avatar_delivery_id_fkey FOREIGN KEY (avatar_delivery_id) REFERENCES public.document_deliveries(id);


--
-- Name: employees employees_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: employees employees_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: employees employees_shift_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_shift_configuration_id_fkey FOREIGN KEY (shift_configuration_id) REFERENCES public.shift_configurations(id);


--
-- Name: employees employees_supervisor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_supervisor_id_fkey FOREIGN KEY (supervisor_id) REFERENCES public.employees(id);


--
-- Name: inbound_pending_uploads inbound_pending_uploads_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.inbound_pending_uploads
    ADD CONSTRAINT inbound_pending_uploads_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: incident_auto_rules incident_auto_rules_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incident_auto_rules
    ADD CONSTRAINT incident_auto_rules_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: incident_notes incident_notes_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incident_notes
    ADD CONSTRAINT incident_notes_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.employees(id);


--
-- Name: incident_notes incident_notes_incident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incident_notes
    ADD CONSTRAINT incident_notes_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES public.incidents(id);


--
-- Name: incidents incidents_break_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_break_id_fkey FOREIGN KEY (break_id) REFERENCES public.work_breaks(id);


--
-- Name: incidents incidents_clock_in_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_clock_in_id_fkey FOREIGN KEY (clock_in_id) REFERENCES public.clock_ins(id);


--
-- Name: incidents incidents_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.employees(id);


--
-- Name: incidents incidents_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: incidents incidents_leave_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_leave_request_id_fkey FOREIGN KEY (leave_request_id) REFERENCES public.leave_requests(id);


--
-- Name: incidents incidents_resolved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_resolved_by_id_fkey FOREIGN KEY (resolved_by_id) REFERENCES public.employees(id);


--
-- Name: incidents incidents_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: invoices invoices_credit_note_for_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_credit_note_for_id_fkey FOREIGN KEY (credit_note_for_id) REFERENCES public.invoices(id);


--
-- Name: invoices invoices_ls_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_ls_payment_id_fkey FOREIGN KEY (ls_payment_id) REFERENCES public.ls_payments(id);


--
-- Name: invoices invoices_stripe_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_stripe_payment_id_fkey FOREIGN KEY (stripe_payment_id) REFERENCES public.stripe_payments(id);


--
-- Name: invoices invoices_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: leave_requests leave_requests_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: leave_requests leave_requests_leave_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_leave_type_id_fkey FOREIGN KEY (leave_type_id) REFERENCES public.leave_types(id);


--
-- Name: leave_requests leave_requests_supervisor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_supervisor_id_fkey FOREIGN KEY (supervisor_id) REFERENCES public.employees(id);


--
-- Name: leave_types leave_types_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.leave_types
    ADD CONSTRAINT leave_types_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: legal_acceptances legal_acceptances_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_acceptances
    ADD CONSTRAINT legal_acceptances_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: legal_acceptances legal_acceptances_legal_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_acceptances
    ADD CONSTRAINT legal_acceptances_legal_document_id_fkey FOREIGN KEY (legal_document_id) REFERENCES public.legal_documents(id);


--
-- Name: legal_documents legal_documents_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_documents
    ADD CONSTRAINT legal_documents_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: legal_tokens legal_tokens_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_tokens
    ADD CONSTRAINT legal_tokens_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: legal_tokens legal_tokens_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.legal_tokens
    ADD CONSTRAINT legal_tokens_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: ls_payments ls_payments_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ls_payments
    ADD CONSTRAINT ls_payments_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscriptions(id);


--
-- Name: ls_payments ls_payments_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.ls_payments
    ADD CONSTRAINT ls_payments_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: mail_logs mail_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.mail_logs
    ADD CONSTRAINT mail_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: notification_preferences notification_preferences_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.notification_preferences
    ADD CONSTRAINT notification_preferences_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: notifications notifications_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: notifications notifications_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: password_reset_tokens password_reset_tokens_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: pending_signups pending_signups_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.pending_signups
    ADD CONSTRAINT pending_signups_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: projects projects_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: shift_assignments shift_assignments_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.shift_assignments
    ADD CONSTRAINT shift_assignments_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: shift_assignments shift_assignments_shift_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.shift_assignments
    ADD CONSTRAINT shift_assignments_shift_configuration_id_fkey FOREIGN KEY (shift_configuration_id) REFERENCES public.shift_configurations(id);


--
-- Name: shift_configurations shift_configurations_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.shift_configurations
    ADD CONSTRAINT shift_configurations_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: signature_envelopes signature_envelopes_document_delivery_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_envelopes
    ADD CONSTRAINT signature_envelopes_document_delivery_id_fkey FOREIGN KEY (document_delivery_id) REFERENCES public.document_deliveries(id);


--
-- Name: signature_envelopes signature_envelopes_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_envelopes
    ADD CONSTRAINT signature_envelopes_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: signature_events signature_events_envelope_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_events
    ADD CONSTRAINT signature_events_envelope_id_fkey FOREIGN KEY (envelope_id) REFERENCES public.signature_envelopes(id);


--
-- Name: signature_notifications signature_notifications_envelope_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_notifications
    ADD CONSTRAINT signature_notifications_envelope_id_fkey FOREIGN KEY (envelope_id) REFERENCES public.signature_envelopes(id);


--
-- Name: signature_notifications signature_notifications_signer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_notifications
    ADD CONSTRAINT signature_notifications_signer_id_fkey FOREIGN KEY (signer_id) REFERENCES public.signature_signers(id);


--
-- Name: signature_otps signature_otps_signer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_otps
    ADD CONSTRAINT signature_otps_signer_id_fkey FOREIGN KEY (signer_id) REFERENCES public.signature_signers(id);


--
-- Name: signature_signers signature_signers_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_signers
    ADD CONSTRAINT signature_signers_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: signature_signers signature_signers_envelope_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.signature_signers
    ADD CONSTRAINT signature_signers_envelope_id_fkey FOREIGN KEY (envelope_id) REFERENCES public.signature_envelopes(id);


--
-- Name: stripe_payments stripe_payments_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.stripe_payments
    ADD CONSTRAINT stripe_payments_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscriptions(id);


--
-- Name: stripe_payments stripe_payments_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.stripe_payments
    ADD CONSTRAINT stripe_payments_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: subscriptions subscriptions_billing_method_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_billing_method_id_fkey FOREIGN KEY (billing_method_id) REFERENCES public.billing_methods(id);


--
-- Name: subscriptions subscriptions_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: subscriptions subscriptions_discount_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_discount_id_fkey FOREIGN KEY (discount_id) REFERENCES public.discounts(id);


--
-- Name: subscriptions subscriptions_pending_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pending_plan_id_fkey FOREIGN KEY (pending_plan_id) REFERENCES public.pricing_plans(id);


--
-- Name: subscriptions subscriptions_pricing_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pricing_plan_id_fkey FOREIGN KEY (pricing_plan_id) REFERENCES public.pricing_plans(id);


--
-- Name: subscriptions subscriptions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: tenants tenants_billing_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_billing_company_id_fkey FOREIGN KEY (billing_company_id) REFERENCES public.companies(id);


--
-- Name: user_groups user_groups_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: webhook_deliveries webhook_deliveries_webhook_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.webhook_deliveries
    ADD CONSTRAINT webhook_deliveries_webhook_id_fkey FOREIGN KEY (webhook_id) REFERENCES public.webhook_endpoints(id);


--
-- Name: webhook_endpoints webhook_endpoints_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.webhook_endpoints
    ADD CONSTRAINT webhook_endpoints_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: work_breaks work_breaks_clock_in_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.work_breaks
    ADD CONSTRAINT work_breaks_clock_in_id_fkey FOREIGN KEY (clock_in_id) REFERENCES public.clock_ins(id);


--
-- Name: work_breaks work_breaks_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.work_breaks
    ADD CONSTRAINT work_breaks_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: work_centers work_centers_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hrm
--

ALTER TABLE ONLY public.work_centers
    ADD CONSTRAINT work_centers_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- PostgreSQL database dump complete
--

\unrestrict r81FeeZUbeVzE0GxxSjDQpkajmY1rvLdfbgFY2pytIluticK8FXk74oVLWAh1lc

