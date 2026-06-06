import { useEffect, useId, useRef } from "react";
import { TabulatorFull as Tabulator } from "tabulator-tables";
import type { CellComponent, ColumnDefinition, TabulatorFull as TabulatorInstance } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import type { ImportColumn } from "../lib/tableImport";
import { ensureTableExportLibs } from "../lib/tableSetup";
import type { BulkImportResult } from "./TableBulkImport";
import TableBulkImport from "./TableBulkImport";

export type { ImportColumn };

export interface DataTableColumn<T extends object = object> {
  title: string;
  field: keyof T & string;
  headerFilter?: boolean | "input" | "select" | "number";
  headerFilterParams?: { values?: Record<string, string>; placeholder?: string };
  width?: number;
  minWidth?: number;
  formatter?: (cell: CellComponent) => string;
  sorter?: boolean | "string" | "number" | "alphanum" | "datetime";
  hozAlign?: "left" | "center" | "right";
  download?: boolean;
  visible?: boolean;
}

export interface DataTableImportConfig {
  templateFilename: string;
  columns: ImportColumn[];
  hint?: string;
  disabled?: boolean;
  onImport: (rows: Record<string, string>[]) => Promise<BulkImportResult>;
}

interface Props<T extends object> {
  data: T[];
  columns: DataTableColumn<T>[];
  loading?: boolean;
  exportFilename?: string;
  height?: string | number;
  selectable?: boolean;
  emptyMessage?: string;
  importConfig?: DataTableImportConfig;
  onImportComplete?: () => void;
  onRowSelectionChange?: (ids: string[]) => void;
  onCellAction?: (action: string, row: T, ctx?: { signerId?: string }) => void;
  onRowClick?: (row: T) => void;
  tableRef?: React.MutableRefObject<TabulatorInstance | null>;
}

function toTabulatorColumns<T extends object>(cols: DataTableColumn<T>[]): ColumnDefinition[] {
  return cols
    .filter((c) => c.visible !== false)
    .map((col) => {
      const def: ColumnDefinition = {
        title: col.title,
        field: col.field as string,
        headerSort: col.sorter !== false,
        headerFilter: col.headerFilter === true ? "input" : col.headerFilter || false,
        headerFilterPlaceholder: col.headerFilterParams?.placeholder ?? "Filtrar…",
        headerFilterLiveFilter: true,
        width: col.width,
        minWidth: col.minWidth,
        hozAlign: col.hozAlign,
        download: col.download !== false,
      };
      if (col.headerFilter === "select" && col.headerFilterParams?.values) {
        def.headerFilter = "list";
        def.headerFilterParams = {
          values: col.headerFilterParams.values,
          clearable: true,
        };
      }
      if (col.formatter) {
        const fmt = col.formatter;
        def.formatter = (cell: CellComponent) => fmt(cell) ?? "";
      }
      if (col.sorter && typeof col.sorter === "string") {
        def.sorter = col.sorter;
      }
      return def;
    });
}

export default function DataTable<T extends object>({
  data,
  columns,
  loading = false,
  exportFilename = "export",
  height = "520px",
  selectable = false,
  emptyMessage = "Sin registros",
  importConfig,
  onImportComplete,
  onRowSelectionChange,
  onCellAction,
  onRowClick,
  tableRef,
}: Props<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<TabulatorInstance | null>(null);
  const builtRef = useRef(false);
  const dataRef = useRef(data);
  const columnsRef = useRef(columns);
  const loadingRef = useRef(loading);
  dataRef.current = data;
  columnsRef.current = columns;
  loadingRef.current = loading;
  const onCellActionRef = useRef(onCellAction);
  const onRowClickRef = useRef(onRowClick);
  const onRowSelectionChangeRef = useRef(onRowSelectionChange);
  onCellActionRef.current = onCellAction;
  onRowClickRef.current = onRowClick;
  onRowSelectionChangeRef.current = onRowSelectionChange;
  const uid = useId().replace(/:/g, "");

  const runWhenReady = (fn: (table: TabulatorInstance) => void) => {
    const table = instanceRef.current;
    if (!table || !builtRef.current) return;
    try {
      fn(table);
    } catch {
      /* tabla destruida o aún montando */
    }
  };

  const syncLoading = (table: TabulatorInstance, isLoading: boolean) => {
    if (isLoading) table.alert("Cargando…");
    else table.clearAlert();
  };

  useEffect(() => {
    ensureTableExportLibs();
    const el = containerRef.current;
    if (!el) return;

    builtRef.current = false;

    const table = new Tabulator(el, {
      data: data as object[],
      columns: toTabulatorColumns(columns),
      layout: "fitColumns",
      layoutColumnsOnNewData: true,
      height,
      placeholder: loading ? "Cargando…" : emptyMessage,
      selectable,
      selectableRangeMode: "click",
      resizableColumnFit: true,
      columnHeaderVertAlign: "middle",
      rowHeader: selectable
        ? {
            formatter: "rowSelection",
            titleFormatter: "rowSelection",
            headerSort: false,
            width: 48,
            minWidth: 48,
            maxWidth: 48,
            resizable: false,
            frozen: true,
          }
        : undefined,
      columnDefaults: {
        headerTooltip: true,
        tooltip: true,
        minWidth: 72,
        vertAlign: "middle",
        headerHozAlign: "left",
        hozAlign: "left",
      },
      pagination: data.length > 80 ? "local" : false,
      paginationSize: 50,
      paginationSizeSelector: [25, 50, 100, 200],
      langs: {
        "es-es": {
          pagination: {
            first: "Primera",
            first_title: "Primera página",
            last: "Última",
            last_title: "Última página",
            prev: "Ant.",
            prev_title: "Anterior",
            next: "Sig.",
            next_title: "Siguiente",
            page_size: "Filas por página",
          },
          headerFilters: {
            default: "Filtrar…",
          },
        },
      },
      locale: "es-es",
    });

    instanceRef.current = table;
    if (tableRef) tableRef.current = table;

    table.on("tableBuilt", () => {
      if (instanceRef.current !== table) return;
      builtRef.current = true;
      table.replaceData(dataRef.current as object[]);
      table.setColumns(toTabulatorColumns(columnsRef.current));
      syncLoading(table, loadingRef.current);
      requestAnimationFrame(() => {
        if (instanceRef.current === table) table.redraw(true);
      });
    });

    table.on("rowSelectionChanged", () => {
      const handler = onRowSelectionChangeRef.current;
      if (!handler) return;
      const selected = table.getSelectedData() as { id?: string }[];
      handler(selected.map((r) => String(r.id ?? "")).filter(Boolean));
    });

    table.on("cellClick", (...args: unknown[]) => {
      const cell = args[1] as CellComponent;
      const ev = args[0] as { target?: EventTarget | null };
      const elTarget = ev?.target as HTMLElement | null;
      const btn = elTarget?.closest?.("[data-action]") as HTMLElement | null;
      const action = btn?.getAttribute("data-action");
      if (!action || !onCellActionRef.current) return;
      const row = cell.getRow().getData() as T;
      const signerId = btn?.getAttribute("data-signer-id") ?? undefined;
      onCellActionRef.current(action, row, signerId ? { signerId } : undefined);
    });

    table.on("rowClick", (...args: unknown[]) => {
      if (!onRowClickRef.current) return;
      const ev = args[0] as { target?: EventTarget | null };
      if ((ev?.target as HTMLElement | null)?.closest?.("[data-action]")) return;
      const row = args[1] as { getData: () => unknown };
      onRowClickRef.current(row.getData() as T);
    });

    return () => {
      builtRef.current = false;
      instanceRef.current = null;
      if (tableRef) tableRef.current = null;
      try {
        table.destroy();
      } catch {
        /* ya destruida */
      }
    };
    // Solo recrear al desmontar; datos/columnas se actualizan en efectos aparte.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const redrawTable = (table: TabulatorInstance) => {
    requestAnimationFrame(() => {
      if (instanceRef.current === table) table.redraw(true);
    });
  };

  useEffect(() => {
    runWhenReady((table) => {
      table.replaceData(data as object[]);
      redrawTable(table);
    });
  }, [data]);

  useEffect(() => {
    runWhenReady((table) => {
      table.setColumns(toTabulatorColumns(columns));
      redrawTable(table);
    });
  }, [columns]);

  useEffect(() => {
    runWhenReady((table) => {
      syncLoading(table, loading);
    });
  }, [loading]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      runWhenReady((table) => table.redraw(true));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const exportTable = (type: "xlsx" | "pdf" | "csv") => {
    const table = instanceRef.current;
    if (!table || !builtRef.current) return;
    const name = exportFilename.replace(/[^\w\-]+/g, "_");
    if (type === "xlsx") table.download("xlsx", `${name}.xlsx`, { sheetName: "Datos" });
    else if (type === "pdf")
      table.download("pdf", `${name}.pdf`, {
        orientation: "landscape",
        title: exportFilename,
      });
    else table.download("csv", `${name}.csv`);
  };

  return (
    <div
      className={`data-table card ${uid}${selectable ? " data-table--selectable" : ""}${onRowClick ? " data-table--row-click" : ""}`}
    >
      <div className="data-table__toolbar">
        <div className="data-table__exports">
          <span className="muted small">Exportar:</span>
          <button type="button" className="btn btn-sm btn-icon" onClick={() => exportTable("xlsx")} title="Excel">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          </button>
          <button type="button" className="btn btn-sm btn-icon" onClick={() => exportTable("pdf")} title="PDF">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          </button>
          <button type="button" className="btn btn-sm btn-icon" onClick={() => exportTable("csv")} title="CSV">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h2v4H8zM12 13h2v4h-2z"/></svg>
          </button>
        </div>
        {importConfig && (
          <TableBulkImport
            templateFilename={importConfig.templateFilename}
            columns={importConfig.columns}
            hint={importConfig.hint}
            disabled={importConfig.disabled}
            onImport={importConfig.onImport}
            onComplete={onImportComplete}
          />
        )}
      </div>
      <div ref={containerRef} className="data-table__grid" />
    </div>
  );
}
