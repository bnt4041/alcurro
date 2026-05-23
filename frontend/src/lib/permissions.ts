import type { Role } from "../api/types";

export type Perm =
  | "employees.read"
  | "employees.write"
  | "employees.delete"
  | "clock_ins.read"
  | "clock_ins.write"
  | "leave.read"
  | "leave.write"
  | "leave.approve"
  | "shifts.read"
  | "shifts.write"
  | "documents.read"
  | "documents.write"
  | "legal.read"
  | "legal.write"
  | "settings.read"
  | "settings.write"
  | "tenant.read"
  | "tenant.write"
  | "tenant.billing"
  | "companies.read"
  | "companies.write"
  | "work_centers.read"
  | "work_centers.write"
  | "departments.read"
  | "departments.write"
  | "groups.read"
  | "groups.write"
  | "gowa.manage";

export type Coarse = "read" | "write" | "admin";

const MODULE_COARSE: Record<string, Record<Coarse, Perm[]>> = {
  employees: {
    read: ["employees.read"],
    write: ["employees.write"],
    admin: ["employees.delete"],
  },
  clock_ins: {
    read: ["clock_ins.read"],
    write: ["clock_ins.write"],
    admin: ["clock_ins.write"],
  },
  leave: {
    read: ["leave.read"],
    write: ["leave.write", "leave.approve"],
    admin: ["leave.approve", "leave.write"],
  },
  shifts: {
    read: ["shifts.read"],
    write: ["shifts.write"],
    admin: ["shifts.write"],
  },
  documents: {
    read: ["documents.read"],
    write: ["documents.write"],
    admin: ["documents.write"],
  },
  legal: {
    read: ["legal.read"],
    write: ["legal.write"],
    admin: ["legal.write"],
  },
  settings: {
    read: ["settings.read"],
    write: ["settings.write"],
    admin: ["settings.write"],
  },
  tenant: {
    read: ["tenant.read"],
    write: ["tenant.write", "tenant.billing"],
    admin: ["tenant.write", "tenant.billing", "gowa.manage"],
  },
  companies: {
    read: ["companies.read"],
    write: ["companies.write"],
    admin: ["companies.write"],
  },
  work_centers: {
    read: ["work_centers.read"],
    write: ["work_centers.write"],
    admin: ["work_centers.write"],
  },
  departments: {
    read: ["departments.read"],
    write: ["departments.write"],
    admin: ["departments.write"],
  },
  groups: {
    read: ["groups.read"],
    write: ["groups.write"],
    admin: ["groups.write"],
  },
};

export function hasPerm(permissions: string[] | undefined, perm: Perm): boolean {
  return permissions?.includes(perm) ?? false;
}

export function canModule(
  permissions: string[] | undefined,
  coarse: Coarse,
  module: string
): boolean {
  const required = MODULE_COARSE[module]?.[coarse] ?? [];
  return required.some((p) => permissions?.includes(p));
}

/** Compatibilidad: admin = tenant.write o módulo admin */
export function can(
  permissions: string[] | undefined,
  coarse: Coarse,
  module = "tenant"
): boolean {
  return canModule(permissions, coarse, module);
}

export const ROLE_LABELS: Record<Role, string> = {
  tenant_admin: "Administrador de cuenta",
  admin: "Administrador de cuenta",
  manager: "Responsable",
  supervisor: "Responsable",
  labor_inspector: "Inspector de Trabajo",
  employee: "Empleado",
};

export const USER_TYPE_OPTIONS: { value: Role; label: string }[] = [
  { value: "tenant_admin", label: "Administrador de cuenta" },
  { value: "manager", label: "Responsable" },
  { value: "labor_inspector", label: "Inspector de Trabajo" },
  { value: "employee", label: "Empleado" },
];

export const PERM_LABELS: Record<Perm, string> = {
  "employees.read": "Ver empleados",
  "employees.write": "Editar empleados",
  "employees.delete": "Eliminar empleados",
  "clock_ins.read": "Ver fichajes",
  "clock_ins.write": "Registrar fichajes",
  "leave.read": "Ver vacaciones",
  "leave.write": "Gestionar vacaciones",
  "leave.approve": "Aprobar vacaciones",
  "shifts.read": "Ver turnos",
  "shifts.write": "Gestionar turnos",
  "documents.read": "Ver documentos",
  "documents.write": "Gestionar documentos",
  "legal.read": "Ver textos legales",
  "legal.write": "Gestionar textos legales",
  "settings.read": "Ver configuración",
  "settings.write": "Editar configuración",
  "tenant.read": "Ver cuenta",
  "tenant.write": "Editar cuenta y branding",
  "tenant.billing": "Datos de facturación",
  "companies.read": "Ver empresas",
  "companies.write": "Gestionar empresas",
  "work_centers.read": "Ver centros",
  "work_centers.write": "Gestionar centros",
  "departments.read": "Ver departamentos",
  "departments.write": "Gestionar departamentos",
  "groups.read": "Ver grupos",
  "groups.write": "Gestionar grupos",
  "gowa.manage": "Gestionar WhatsApp",
};
