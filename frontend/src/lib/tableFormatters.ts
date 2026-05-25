/** HTML para celdas de acción en Tabulator (data-action para DataTable.onCellAction). */
export type TableAction = { id: string; label: string; className?: string };

export function tableActionButtons(actions: TableAction[]): string {
  return actions
    .map(
      (a) =>
        `<button type="button" class="btn btn-sm ${a.className ?? ""}" data-action="${a.id}">${a.label}</button>`
    )
    .join(" ");
}
