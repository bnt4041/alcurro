import type { Employee, WorkScheduleBlock } from "../api/types";

export const WORK_DAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

export function toTimeInput(value: string | null | undefined): string {
  if (!value) return "";
  return value.slice(0, 5);
}

function formatDayRange(days: number[]): string {
  if (days.length === 7) return "todos";
  if (days.length === 5 && [0, 1, 2, 3, 4].every((d) => days.includes(d))) return "Lun–Vie";
  if (days.length === 4 && [0, 1, 2, 3].every((d) => days.includes(d))) return "Lun–Jue";
  return days
    .slice()
    .sort((a, b) => a - b)
    .map((d) => WORK_DAY_LABELS[d])
    .join(", ");
}

function formatBlock(block: WorkScheduleBlock): string {
  const hours = `${toTimeInput(block.work_start_time)}–${toTimeInput(block.work_end_time)}`;
  const breakStr = block.break_minutes > 0 ? ` (${block.break_minutes} min break)` : "";
  return `${formatDayRange(block.work_days)} ${hours}${breakStr}`;
}

export function blocksFromEmployee(emp: Partial<Employee>): WorkScheduleBlock[] {
  if (emp.work_schedule_blocks?.length) return emp.work_schedule_blocks;
  return [
    {
      work_days: emp.work_days?.length ? emp.work_days : [0, 1, 2, 3, 4],
      work_start_time: emp.work_start_time ?? "09:00:00",
      work_end_time: emp.work_end_time ?? "18:00:00",
      break_minutes: 0,
    },
  ];
}

export function defaultScheduleBlocks(): WorkScheduleBlock[] {
  return [
    {
      work_days: [0, 1, 2, 3],
      work_start_time: "09:00:00",
      work_end_time: "18:00:00",
      break_minutes: 60,
    },
    {
      work_days: [4],
      work_start_time: "08:00:00",
      work_end_time: "15:00:00",
      break_minutes: 0,
    },
  ];
}

export function formatWorkSchedule(emp: Partial<Employee>): string {
  const blocks = blocksFromEmployee(emp);
  if (!blocks.length) return "—";
  return blocks.map(formatBlock).join(" · ") || "—";
}
