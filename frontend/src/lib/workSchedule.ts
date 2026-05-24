import type {
  Employee,
  WorkScheduleDayBlock,
  WorkSchedulePeriod,
  WorkScheduleTimeSlot,
} from "../api/types";

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

function formatSlot(slot: WorkScheduleTimeSlot): string {
  const hours = `${toTimeInput(slot.work_start_time)}–${toTimeInput(slot.work_end_time)}`;
  return slot.break_minutes > 0 ? `${hours} (${slot.break_minutes}m break)` : hours;
}

function normalizeDayBlock(raw: Record<string, unknown>): WorkScheduleDayBlock {
  if (Array.isArray(raw.slots) && raw.slots.length) {
    return {
      work_days: (raw.work_days as number[]) ?? [],
      slots: (raw.slots as WorkScheduleTimeSlot[]).map((s) => ({
        work_start_time: s.work_start_time,
        work_end_time: s.work_end_time,
        break_minutes: s.break_minutes ?? 0,
      })),
    };
  }
  return {
    work_days: (raw.work_days as number[]) ?? [0, 1, 2, 3, 4],
    slots: [
      {
        work_start_time: (raw.work_start_time as string) ?? "09:00:00",
        work_end_time: (raw.work_end_time as string) ?? "18:00:00",
        break_minutes: (raw.break_minutes as number) ?? 0,
      },
    ],
  };
}

export function emptyTimeSlot(): WorkScheduleTimeSlot {
  return { work_start_time: "09:00:00", work_end_time: "14:00:00", break_minutes: 0 };
}

export function emptyDayBlock(): WorkScheduleDayBlock {
  return { work_days: [0, 1, 2, 3], slots: [emptyTimeSlot()] };
}

export function defaultSchedulePeriods(): WorkSchedulePeriod[] {
  const year = new Date().getFullYear();
  return [
    {
      valid_from: `${year}-01-01`,
      valid_to: null,
      blocks: [
        {
          work_days: [0, 1, 2, 3],
          slots: [
            { work_start_time: "09:00:00", work_end_time: "14:00:00", break_minutes: 0 },
            { work_start_time: "16:00:00", work_end_time: "18:00:00", break_minutes: 0 },
          ],
        },
        {
          work_days: [4],
          slots: [{ work_start_time: "08:00:00", work_end_time: "15:00:00", break_minutes: 0 }],
        },
      ],
    },
  ];
}

export function periodsFromEmployee(emp: Partial<Employee>): WorkSchedulePeriod[] {
  if (emp.work_schedule_periods?.length) {
    return emp.work_schedule_periods.map((p) => ({
      valid_from: p.valid_from,
      valid_to: p.valid_to,
      blocks: p.blocks.map((b) => normalizeDayBlock(b as unknown as Record<string, unknown>)),
    }));
  }
  if (emp.work_schedule_blocks?.length) {
    const year = new Date().getFullYear();
    return [
      {
        valid_from: `${year}-01-01`,
        valid_to: null,
        blocks: emp.work_schedule_blocks.map((b) =>
          normalizeDayBlock(b as unknown as Record<string, unknown>)
        ),
      },
    ];
  }
  return defaultSchedulePeriods();
}

function formatDayBlock(block: WorkScheduleDayBlock): string {
  const slots = block.slots.map(formatSlot).join(" + ");
  return `${formatDayRange(block.work_days)} ${slots}`;
}

function formatPeriod(period: WorkSchedulePeriod): string {
  const from = period.valid_from;
  const to = period.valid_to ? ` → ${period.valid_to}` : "";
  const blocks = period.blocks.map(formatDayBlock).join(" · ");
  return `[${from}${to}] ${blocks}`;
}

export function formatWorkSchedule(emp: Partial<Employee>): string {
  if (emp.rotating_shift) return "Turno rotativo (complejo)";
  const periods = periodsFromEmployee(emp);
  if (!periods.length) return "—";
  return periods.map(formatPeriod).join(" | ") || "—";
}

export function validatePeriodsClient(periods: WorkSchedulePeriod[]): string | null {
  if (!periods.length) return "Añade al menos un periodo de horario";
  for (let pi = 0; pi < periods.length; pi++) {
    const p = periods[pi];
    if (!p.valid_from) return `Periodo ${pi + 1}: indica fecha de inicio`;
    if (p.valid_to && p.valid_to < p.valid_from) {
      return `Periodo ${pi + 1}: la fecha fin no puede ser anterior al inicio`;
    }
    if (!p.blocks.length) return `Periodo ${pi + 1}: añade al menos un bloque de días`;
    const seen = new Set<number>();
    for (const block of p.blocks) {
      if (!block.work_days.length) {
        return `Periodo ${pi + 1}: cada bloque debe tener al menos un día`;
      }
      for (const d of block.work_days) {
        if (seen.has(d)) {
          return `Periodo ${pi + 1}: un día no puede repetirse en varios bloques`;
        }
        seen.add(d);
      }
      if (!block.slots.length) {
        return `Periodo ${pi + 1}: añade al menos una franja horaria por bloque`;
      }
      for (const slot of block.slots) {
        if (slot.work_start_time >= slot.work_end_time) {
          return `Periodo ${pi + 1}: inicio de franja debe ser anterior al fin`;
        }
      }
    }
  }
  const sorted = [...periods].sort((a, b) => a.valid_from.localeCompare(b.valid_from));
  for (let i = 0; i < sorted.length - 1; i++) {
    const a = sorted[i];
    const b = sorted[i + 1];
    const aEnd = a.valid_to || "9999-12-31";
    if (b.valid_from <= aEnd) {
      return "Los periodos no pueden solaparse en fechas";
    }
  }
  return null;
}
