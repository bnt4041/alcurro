import type { WorkScheduleBlock } from "../api/types";
import { WORK_DAY_LABELS, toTimeInput } from "../lib/workSchedule";

export const emptyScheduleBlock = (): WorkScheduleBlock => ({
  work_days: [0, 1, 2, 3],
  work_start_time: "09:00:00",
  work_end_time: "18:00:00",
  break_minutes: 60,
});

interface Props {
  blocks: WorkScheduleBlock[];
  onChange: (blocks: WorkScheduleBlock[]) => void;
  shiftConfigs?: { id: string; name: string }[];
  shiftConfigurationId?: string | null;
  onShiftChange?: (id: string | null) => void;
}

export default function WorkScheduleEditor({
  blocks,
  onChange,
  shiftConfigs = [],
  shiftConfigurationId,
  onShiftChange,
}: Props) {
  const updateBlock = (index: number, patch: Partial<WorkScheduleBlock>) => {
    const next = blocks.map((b, i) => (i === index ? { ...b, ...patch } : b));
    onChange(next);
  };

  const toggleDay = (index: number, day: number) => {
    const block = blocks[index];
    const usedElsewhere = blocks.some(
      (b, i) => i !== index && b.work_days.includes(day)
    );
    if (usedElsewhere && !block.work_days.includes(day)) return;
    const days = block.work_days.includes(day)
      ? block.work_days.filter((d) => d !== day)
      : [...block.work_days, day].sort((a, b) => a - b);
    updateBlock(index, { work_days: days });
  };

  const addBlock = () => {
    const used = new Set(blocks.flatMap((b) => b.work_days));
    const free = [0, 1, 2, 3, 4, 5, 6].filter((d) => !used.has(d));
    onChange([
      ...blocks,
      {
        work_days: free.length ? [free[0]] : [],
        work_start_time: "09:00:00",
        work_end_time: "18:00:00",
        break_minutes: 0,
      },
    ]);
  };

  const removeBlock = (index: number) => {
    if (blocks.length <= 1) return;
    onChange(blocks.filter((_, i) => i !== index));
  };

  return (
    <fieldset className="form-grid-full schedule-blocks-fieldset">
      <legend>Horario de trabajo</legend>
      <p className="muted small form-grid-full">
        Puedes definir varios bloques (p. ej. L–J 09:00–18:00 con 1 h de descanso y V
        08:00–15:00 sin break). Cada día solo puede pertenecer a un bloque.
      </p>

      {shiftConfigs.length > 0 && onShiftChange && (
        <label className="form-grid-full">
          Turno (opcional)
          <select
            value={shiftConfigurationId ?? ""}
            onChange={(e) => onShiftChange(e.target.value || null)}
          >
            <option value="">Sin turno asignado</option>
            {shiftConfigs.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {blocks.map((block, index) => (
        <div key={index} className="schedule-block card-inner form-grid-full">
          <div className="schedule-block__header">
            <strong>Bloque {index + 1}</strong>
            {blocks.length > 1 && (
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                onClick={() => removeBlock(index)}
              >
                Quitar bloque
              </button>
            )}
          </div>
          <label>
            Hora inicio
            <input
              type="time"
              value={toTimeInput(block.work_start_time)}
              onChange={(e) =>
                updateBlock(index, {
                  work_start_time: e.target.value ? `${e.target.value}:00` : "09:00:00",
                })
              }
            />
          </label>
          <label>
            Hora fin
            <input
              type="time"
              value={toTimeInput(block.work_end_time)}
              onChange={(e) =>
                updateBlock(index, {
                  work_end_time: e.target.value ? `${e.target.value}:00` : "18:00:00",
                })
              }
            />
          </label>
          <label>
            Descanso (min)
            <input
              type="number"
              min={0}
              max={480}
              step={15}
              value={block.break_minutes}
              onChange={(e) =>
                updateBlock(index, {
                  break_minutes: Math.max(0, parseInt(e.target.value, 10) || 0),
                })
              }
            />
          </label>
          <div className="form-grid-full">
            <span className="label-like">Días</span>
            <div className="day-chips">
              {WORK_DAY_LABELS.map((label, day) => {
                const usedElsewhere = blocks.some(
                  (b, i) => i !== index && b.work_days.includes(day)
                );
                return (
                  <label
                    key={day}
                    className={`checkbox chip ${usedElsewhere ? "chip--disabled" : ""}`}
                    title={usedElsewhere ? "Ya asignado a otro bloque" : undefined}
                  >
                    <input
                      type="checkbox"
                      checked={block.work_days.includes(day)}
                      disabled={usedElsewhere}
                      onChange={() => toggleDay(index, day)}
                    />
                    {label}
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      ))}

      <button type="button" className="btn btn-sm form-grid-full" onClick={addBlock}>
        + Añadir bloque de horario
      </button>
    </fieldset>
  );
}
