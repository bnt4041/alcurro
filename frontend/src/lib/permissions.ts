import type { Role } from "../api/types";

export type Perm =
  | "employees.read"
  | "employees.read_own"
  | "employees.write"
  | "employees.create_own"
  | "employees.update_own"
  | "employees.delete"
  | "clock_ins.read"
  | "clock_ins.read_own"
  | "clock_ins.write"
  | "clock_ins.create_own"
  | "clock_ins.update_own"
  | "breaks.read"
  | "breaks.read_own"
  | "breaks.write"
  | "breaks.create_own"
  | "breaks.update_own"
  | "leave.read"
  | "leave.read_own"
  | "leave.write"
  | "leave.create_own"
  | "leave.update_own"
  | "leave.approve"
  | "shifts.read"
  | "shifts.read_own"
  | "shifts.write"
  | "shifts.create_own"
  | "shifts.update_own"
  | "documents.read"
  | "documents.read_own"
  | "documents.write"
  | "documents.create_own"
  | "documents.update_own"
  | "documents.bulk"
  | "signatures.read"
  | "signatures.read_own"
  | "signatures.write"
  | "signatures.create_own"
  | "signatures.update_own"
  | "legal.read"
  | "legal.read_own"
  | "legal.write"
  | "legal.create_own"
  | "legal.update_own"
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

export type Coarse = "read" | "write" | "admin" | "create" | "update";

const MODULE_COARSE: Record<string, Record<Coarse, Perm[]>> = {
  employees: {
    read: ["employees.read", "employees.read_own"],
    write: ["employees.write", "employees.create_own", "employees.update_own"],
    create: ["employees.write", "employees.create_own"],
    update: ["employees.write", "employees.update_own"],
    admin: ["employees.delete"],
  },
  clock_ins: {
    read: ["clock_ins.read", "clock_ins.read_own"],
    write: ["clock_ins.write", "clock_ins.create_own", "clock_ins.update_own"],
    create: ["clock_ins.write", "clock_ins.create_own"],
    update: ["clock_ins.write", "clock_ins.update_own"],
    admin: ["clock_ins.write"],
  },
  breaks: {
    read: ["breaks.read", "breaks.read_own"],
    write: ["breaks.write", "breaks.create_own", "breaks.update_own"],
    create: ["breaks.write", "breaks.create_own"],
    update: ["breaks.write", "breaks.update_own"],
    admin: ["breaks.write"],
  },
  leave: {
    read: ["leave.read", "leave.read_own"],
    write: ["leave.write", "leave.create_own", "leave.update_own", "leave.approve"],
    create: ["leave.write", "leave.create_own"],
    update: ["leave.write", "leave.update_own", "leave.approve"],
    admin: ["leave.approve", "leave.write"],
  },
  shifts: {
    read: ["shifts.read", "shifts.read_own"],
    write: ["shifts.write", "shifts.create_own", "shifts.update_own"],
    create: ["shifts.write", "shifts.create_own"],
    update: ["shifts.write", "shifts.update_own"],
    admin: ["shifts.write"],
  },
  documents: {
    read: ["documents.read", "documents.read_own"],
    write: ["documents.write", "documents.create_own", "documents.update_own"],
    create: ["documents.write", "documents.create_own"],
    update: ["documents.write", "documents.update_own"],
    admin: ["documents.write"],
  },
  signatures: {
    read: [
      "signatures.read",
      "signatures.read_own",
      "documents.read",
      "documents.read_own",
    ],
    write: [
      "signatures.write",
      "signatures.create_own",
      "signatures.update_own",
      "documents.write",
      "documents.create_own",
      "documents.update_own",
    ],
    create: [
      "signatures.write",
      "signatures.create_own",
      "documents.write",
      "documents.create_own",
    ],
    update: [
      "signatures.write",
      "signatures.update_own",
      "documents.write",
      "documents.update_own",
    ],
    admin: ["signatures.write", "documents.write"],
  },
  legal: {
    read: ["legal.read", "legal.read_own"],
    write: ["legal.write", "legal.create_own", "legal.update_own"],
    create: ["legal.write", "legal.create_own"],
    update: ["legal.write", "legal.update_own"],
    admin: ["legal.write"],
  },
  settings: {
    read: ["settings.read"],
    write: ["settings.write"],
    create: ["settings.write"],
    update: ["settings.write"],
    admin: ["settings.write"],
  },
  tenant: {
    read: ["tenant.read"],
    write: ["tenant.write", "tenant.billing"],
    create: ["tenant.write", "tenant.billing"],
    update: ["tenant.write", "tenant.billing"],
    admin: ["tenant.write", "tenant.billing", "gowa.manage"],
  },
  companies: {
    read: ["companies.read"],
    write: ["companies.write"],
    create: ["companies.write"],
    update: ["companies.write"],
    admin: ["companies.write"],
  },
  work_centers: {
    read: ["work_centers.read"],
    write: ["work_centers.write"],
    create: ["work_centers.write"],
    update: ["work_centers.write"],
    admin: ["work_centers.write"],
  },
  departments: {
    read: ["departments.read"],
    write: ["departments.write"],
    create: ["departments.write"],
    update: ["departments.write"],
    admin: ["departments.write"],
  },
  groups: {
    read: ["groups.read"],
    write: ["groups.write"],
    create: ["groups.write"],
    update: ["groups.write"],
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
  "employees.read": "Ver todos los empleados",
  "employees.read_own": "Ver sólo los del usuario",
  "employees.write": "Crear y modificar todos",
  "employees.create_own": "Crear sólo los del usuario",
  "employees.update_own": "Modificar sólo los del usuario",
  "employees.delete": "Eliminar empleados",
  "clock_ins.read": "Ver todos los fichajes",
  "clock_ins.read_own": "Ver sólo los del usuario",
  "clock_ins.write": "Crear y modificar todos",
  "clock_ins.create_own": "Crear sólo los del usuario",
  "clock_ins.update_own": "Modificar sólo los del usuario",
  "breaks.read": "Ver todas las paradas",
  "breaks.read_own": "Ver sólo las del usuario",
  "breaks.write": "Crear y modificar todas",
  "breaks.create_own": "Crear sólo las del usuario",
  "breaks.update_own": "Modificar sólo las del usuario",
  "leave.read": "Ver todas las vacaciones",
  "leave.read_own": "Ver sólo las del usuario",
  "leave.write": "Gestionar todas las vacaciones",
  "leave.create_own": "Crear sólo las del usuario",
  "leave.update_own": "Modificar sólo las del usuario",
  "leave.approve": "Aprobar vacaciones",
  "shifts.read": "Ver todos los turnos",
  "shifts.read_own": "Ver sólo los del usuario",
  "shifts.write": "Crear y modificar todos",
  "shifts.create_own": "Crear sólo los del usuario",
  "shifts.update_own": "Modificar sólo los del usuario",
  "documents.read": "Ver todos los documentos",
  "documents.read_own": "Ver sólo los del usuario",
  "documents.write": "Crear y modificar todos",
  "documents.create_own": "Crear sólo los del usuario",
  "documents.update_own": "Modificar sólo los del usuario",
  "documents.bulk": "Subida masiva de nóminas",
  "signatures.read": "Ver todas las firmas",
  "signatures.read_own": "Ver sólo las del usuario",
  "signatures.write": "Crear y modificar todas",
  "signatures.create_own": "Crear sólo las del usuario",
  "signatures.update_own": "Modificar sólo las del usuario",
  "legal.read": "Ver textos legales (todos)",
  "legal.read_own": "Ver sólo cumplimiento del usuario",
  "legal.write": "Gestionar textos legales",
  "legal.create_own": "Crear sólo los del usuario",
  "legal.update_own": "Modificar sólo los del usuario",
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

export const PERM_SECTIONS: { section: string; keys: Perm[] }[] = [
  {
    section: "Empleados",
    keys: [
      "employees.read",
      "employees.read_own",
      "employees.write",
      "employees.create_own",
      "employees.update_own",
      "employees.delete",
    ],
  },
  {
    section: "Fichajes",
    keys: [
      "clock_ins.read",
      "clock_ins.read_own",
      "clock_ins.write",
      "clock_ins.create_own",
      "clock_ins.update_own",
    ],
  },
  {
    section: "Paradas",
    keys: [
      "breaks.read",
      "breaks.read_own",
      "breaks.write",
      "breaks.create_own",
      "breaks.update_own",
    ],
  },
  {
    section: "Vacaciones",
    keys: [
      "leave.read",
      "leave.read_own",
      "leave.write",
      "leave.create_own",
      "leave.update_own",
      "leave.approve",
    ],
  },
  {
    section: "Turnos",
    keys: [
      "shifts.read",
      "shifts.read_own",
      "shifts.write",
      "shifts.create_own",
      "shifts.update_own",
    ],
  },
  {
    section: "Documentos",
    keys: [
      "documents.read",
      "documents.read_own",
      "documents.write",
      "documents.create_own",
      "documents.update_own",
      "documents.bulk",
    ],
  },
  {
    section: "Firmas electrónicas",
    keys: [
      "signatures.read",
      "signatures.read_own",
      "signatures.write",
      "signatures.create_own",
      "signatures.update_own",
    ],
  },
  {
    section: "Textos legales",
    keys: [
      "legal.read",
      "legal.read_own",
      "legal.write",
      "legal.create_own",
      "legal.update_own",
    ],
  },
  {
    section: "Organización",
    keys: [
      "companies.read",
      "companies.write",
      "work_centers.read",
      "work_centers.write",
      "departments.read",
      "departments.write",
    ],
  },
  {
    section: "Grupos y permisos",
    keys: ["groups.read", "groups.write"],
  },
  {
    section: "Cuenta",
    keys: ["tenant.read", "tenant.write", "tenant.billing", "gowa.manage"],
  },
  {
    section: "Configuración sistema",
    keys: ["settings.read", "settings.write"],
  },
];
