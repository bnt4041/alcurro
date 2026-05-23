import type { Employee } from "../api/types";

export const WORK_DAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

export function toTimeInput(value: string | null | undefined): string {
  if (!value) return "";
  return value.slice(0, 5);
}

export function formatWorkSchedule(emp: Partial<Employee>): string {
  const days = emp.work_days ?? [];
  if (!emp.work_start_time && !emp.work_end_time && days.length === 0) return "—";
  const hours =
    emp.work_start_time && emp.work_end_time
      ? `${toTimeInput(emp.work_start_time)}–${toTimeInput(emp.work_end_time)}`
      : emp.work_start_time || emp.work_end_time
        ? toTimeInput(emp.work_start_time ?? emp.work_end_time)
        : "";
  const dayStr =
    days.length === 7
      ? "todos"
      : days.length === 5 && [0, 1, 2, 3, 4].every((d) => days.includes(d))
        ? "Lun–Vie"
        : days
            .slice()
            .sort((a, b) => a - b)
            .map((d) => WORK_DAY_LABELS[d])
            .join(", ");
  return [hours, dayStr].filter(Boolean).join(" · ") || "—";
}
