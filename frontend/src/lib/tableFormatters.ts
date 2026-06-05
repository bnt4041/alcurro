/** HTML para celdas de acción en Tabulator (data-action para DataTable.onCellAction). */
export type TableAction = { id: string; label: string; className?: string };

/** Iconos SVG inline — estilo Feather/Heroicons, 18px, trazo 1.5 */
function svgIcon(pathData: string): string {
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="${pathData}"/></svg>`;
}

/** Mapa de iconos SVG por acción */
const ICONS: Record<string, string> = {
  edit:         svgIcon("M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7 M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"),
  delete:       svgIcon("M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 M10 11v6 M14 11v6"),
  toggle:       svgIcon("M1 4h4l2 2h10l2-2h4 M4 4v16 M20 4v16 M12 8v8 M9 11l3-3 3 3"),
  password:     svgIcon("M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"),
  download:     svgIcon("M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3"),
  whatsapp:     svgIcon("M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"),
  view:         svgIcon("M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"),
  resend:       svgIcon("M21 2v6h-6 M3 12a9 9 0 0 1 15-6.7L21 8 M3 22v-6h6 M21 12a9 9 0 0 1-15 6.7L3 16"),
  add:          svgIcon("M12 5v14 M5 12h14"),
  up:           svgIcon("M18 15l-6-6-6 6"),
  down:         svgIcon("M6 9l6 6 6-6"),
  moveup:       svgIcon("M18 15l-6-6-6 6"),
  movedown:     svgIcon("M6 9l6 6 6-6"),
  cancel:       svgIcon("M18 6 6 18 M6 6l12 12"),
  confirm:      svgIcon("M20 6 9 17l-5-5"),
  signed:       svgIcon("M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4 M10 17l-3-3 1.5-1.5L10 14l4.5-5.5L16 10l-6 7z M3 13V3h4 M5 3 3 5l2 2"),
  certificate:  svgIcon("M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0 1 12 2.944a11.955 11.955 0 0 1-8.618 3.04A12.02 12.02 0 0 0 3 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"),
  approve:      svgIcon("M20 6 9 17l-5-5"),
  reject:       svgIcon("M18 6 6 18 M6 6l12 12"),
};

/** Botones de acción con icono SVG + tooltip. */
export function tableActionButtons(actions: TableAction[]): string {
  return actions
    .map((a) => {
      const icon = ICONS[a.id] ?? a.label;
      return `<button type="button" class="btn btn-sm btn-icon ${a.className ?? ""}" data-action="${a.id}" title="${a.label}">${icon}</button>`;
    })
    .join(" ");
}
