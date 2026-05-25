/** Registra librerías de exportación para Tabulator (xlsx, pdf). */
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";

let done = false;

export function ensureTableExportLibs(): void {
  if (done) return;
  const g = globalThis as typeof globalThis & {
    XLSX?: typeof XLSX;
    jsPDF?: typeof jsPDF;
  };
  g.XLSX = XLSX;
  g.jsPDF = jsPDF;
  done = true;
  void autoTable;
}
