import type {
  WorkScheduleDayBlock,
  WorkSchedulePeriod,
  WorkScheduleTimeSlot,
} from "../api/types";
import {
  WORK_DAY_LABELS,
  emptyDayBlock,
  emptyTimeSlot,
  toTimeInput,
} from "../lib/workSchedule";

interface Props {
  periods: WorkSchedulePeriod[];
  onChange: (periods: WorkSchedulePeriod[]) => void;
  shiftConfigs?: { id: string; name: string }[];
  shiftConfigurationId?: string | null;
  onShiftChange?: (id: string | null) => void;
}

export default function WorkScheduleEditor({
  periods,
  onChange,
  shiftConfigs = [],
  shiftConfigurationId,
  onShiftChange,
}: Props) {
  const updatePeriods = (next: WorkSchedulePeriod[]) => onChange(next);

  const updatePeriod = (pi: number, patch: Partial<WorkSchedulePeriod>) => {
    updatePeriods(periods.map((p, i) => (i === pi ? { ...p, ...patch } : p)));
  };

  const updateBlock = (pi: number, bi: number, patch: Partial<WorkScheduleDayBlock>) => {
    const blocks = periods[pi].blocks.map((b, i) => (i === bi ? { ...b, ...patch } : b));
    updatePeriod(pi, { blocks });
  };

  const updateSlot = (
    pi: number,
    bi: number,
    si: number,
    patch: Partial<WorkScheduleTimeSlot>
  ) => {
    const slots = periods[pi].blocks[bi].slots.map((s, i) =>
      i === si ? { ...s, ...patch } : s
    );
    updateBlock(pi, bi, { slots });
  };

  const toggleDay = (pi: number, bi: number, day: number) => {
    const block = periods[pi].blocks[bi];
    const usedElsewhere = periods[pi].blocks.some(
      (b, i) => i !== bi && b.work_days.includes(day)
    );
    if (usedElsewhere && !block.work_days.includes(day)) return;
    const days = block.work_days.includes(day)
      ? block.work_days.filter((d) => d !== day)
      : [...block.work_days, day].sort((a, b) => a - b);
    updateBlock(pi, bi, { work_days: days });
  };

  const addPeriod = () => {
    const year = new Date().getFullYear();
    updatePeriods([
      ...periods,
      {
        valid_from: `${year}-01-01`,
        valid_to: null,
        blocks: [emptyDayBlock()],
      },
    ]);
  };

  const removePeriod = (pi: number) => {
    if (periods.length <= 1) return;
    updatePeriods(periods.filter((_, i) => i !== pi));
  };

  const addBlock = (pi: number) => {
    const used = new Set(periods[pi].blocks.flatMap((b) => b.work_days));
    const free = [0, 1, 2, 3, 4, 5, 6].filter((d) => !used.has(d));
    updatePeriod(pi, {
      blocks: [
        ...periods[pi].blocks,
        {
          work_days: free.length ? [free[0]] : [],
          slots: [emptyTimeSlot()],
        },
      ],
    });
  };

  const removeBlock = (pi: number, bi: number) => {
    if (periods[pi].blocks.length <= 1) return;
    updatePeriod(pi, { blocks: periods[pi].blocks.filter((_, i) => i !== bi) });
  };

  const addSlot = (pi: number, bi: number) => {
    updateBlock(pi, bi, {
      slots: [...periods[pi].blocks[bi].slots, emptyTimeSlot()],
    });
  };

  const removeSlot = (pi: number, bi: number, si: number) => {
    if (periods[pi].blocks[bi].slots.length <= 1) return;
    updateBlock(pi, bi, {
      slots: periods[pi].blocks[bi].slots.filter((_, i) => i !== si),
    });
  };

  return (
    <div className="schedule-editor form-grid-full">
      <div className="schedule-editor__head">
        <h3 className="schedule-editor__title">Horario de trabajo</h3>
        <p className="muted small">
          Define uno o más periodos con fechas (p. ej. 01/01/2026–31/07/2026). En cada periodo
          puedes crear varios bloques de días y, en cada bloque, varias franjas (turno partido).
        </p>
      </div>

      {shiftConfigs.length > 0 && onShiftChange && (
        <label className="form-grid-full">
          Turno complejo (opcional)
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

      {periods.map((period, pi) => (
        <section key={pi} className="schedule-period card">
          <div className="schedule-period__header">
            <strong>Periodo {pi + 1}</strong>
            {periods.length > 1 && (
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                onClick={() => removePeriod(pi)}
              >
                Quitar periodo
              </button>
            )}
          </div>
          <div className="schedule-period__dates">
            <label>
              Válido desde
              <input
                type="date"
                required
                value={period.valid_from}
                onChange={(e) => updatePeriod(pi, { valid_from: e.target.value })}
              />
            </label>
            <label>
              Válido hasta
              <input
                type="date"
                value={period.valid_to ?? ""}
                onChange={(e) =>
                  updatePeriod(pi, { valid_to: e.target.value || null })
                }
              />
              <span className="muted small">Vacío = sin fecha de fin</span>
            </label>
          </div>

          {period.blocks.map((block, bi) => (
            <div key={bi} className="schedule-block">
              <div className="schedule-block__header">
                <span>Bloque de días {bi + 1}</span>
                {period.blocks.length > 1 && (
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost"
                    onClick={() => removeBlock(pi, bi)}
                  >
                    Quitar bloque
                  </button>
                )}
              </div>

              <div className="schedule-block__days">
                <span className="label-like">Días</span>
                <div className="day-chips">
                  {WORK_DAY_LABELS.map((label, day) => {
                    const usedElsewhere = period.blocks.some(
                      (b, i) => i !== bi && b.work_days.includes(day)
                    );
                    return (
                      <label
                        key={day}
                        className={`checkbox chip ${usedElsewhere ? "chip--disabled" : ""}`}
                        title={usedElsewhere ? "Ya en otro bloque" : undefined}
                      >
                        <input
                          type="checkbox"
                          checked={block.work_days.includes(day)}
                          disabled={usedElsewhere}
                          onChange={() => toggleDay(pi, bi, day)}
                        />
                        {label}
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="schedule-slots">
                <span className="label-like">Franjas horarias</span>
                {block.slots.map((slot, si) => (
                  <div key={si} className="schedule-slot">
                    <span className="schedule-slot__label">Franja {si + 1}</span>
                    <label>
                      Inicio
                      <input
                        type="time"
                        value={toTimeInput(slot.work_start_time)}
                        onChange={(e) =>
                          updateSlot(pi, bi, si, {
                            work_start_time: e.target.value
                              ? `${e.target.value}:00`
                              : "09:00:00",
                          })
                        }
                      />
                    </label>
                    <label>
                      Fin
                      <input
                        type="time"
                        value={toTimeInput(slot.work_end_time)}
                        onChange={(e) =>
                          updateSlot(pi, bi, si, {
                            work_end_time: e.target.value
                              ? `${e.target.value}:00`
                              : "18:00:00",
                          })
                        }
                      />
                    </label>
                    <label>
                      Break (min)
                      <input
                        type="number"
                        min={0}
                        max={480}
                        step={15}
                        value={slot.break_minutes}
                        onChange={(e) =>
                          updateSlot(pi, bi, si, {
                            break_minutes: Math.max(0, parseInt(e.target.value, 10) || 0),
                          })
                        }
                      />
                    </label>
                    {block.slots.length > 1 && (
                      <button
                        type="button"
                        className="btn btn-sm btn-ghost schedule-slot__remove"
                        onClick={() => removeSlot(pi, bi, si)}
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => addSlot(pi, bi)}
                >
                  + Franja horaria
                </button>
              </div>
            </div>
          ))}

          <button type="button" className="btn btn-sm" onClick={() => addBlock(pi)}>
            + Bloque de días
          </button>
        </section>
      ))}

      <button type="button" className="btn btn-sm" onClick={addPeriod}>
        + Añadir periodo (otras fechas)
      </button>
    </div>
  );
}
