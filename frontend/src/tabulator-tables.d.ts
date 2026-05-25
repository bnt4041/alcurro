declare module "tabulator-tables" {
  export type CellComponent = {
    getValue: () => unknown;
    getRow: () => { getData: () => unknown };
  };

  export type ColumnDefinition = Record<string, unknown>;

  export class TabulatorFull {
    constructor(element: HTMLElement, options?: Record<string, unknown>);
    setData(data: unknown[]): void;
    replaceData(data: unknown[]): void;
    setColumns(columns: ColumnDefinition[]): void;
    destroy(): void;
    download(type: string, filename: string, options?: Record<string, unknown>): void;
    alert(message: string): void;
    clearAlert(): void;
    redraw(force?: boolean): void;
    on(event: string, callback: (...args: unknown[]) => void): void;
    getSelectedData(): unknown[];
  }

  export { TabulatorFull as Tabulator };
}
