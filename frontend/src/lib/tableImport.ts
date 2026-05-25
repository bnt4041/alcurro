import * as XLSX from "xlsx";

export interface ImportColumn {
  key: string;
  header: string;
  example?: string;
}

export function downloadImportTemplate(
  filename: string,
  columns: ImportColumn[]
): void {
  const headers = columns.map((c) => c.header);
  const example = columns.map((c) => c.example ?? "");
  const ws = XLSX.utils.aoa_to_sheet([headers, example]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Plantilla");
  XLSX.writeFile(wb, filename.endsWith(".xlsx") ? filename : `${filename}.xlsx`);
}

export async function parseSpreadsheetFile(
  file: File
): Promise<Record<string, string>[]> {
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { type: "array" });
  const sheet = wb.Sheets[wb.SheetNames[0]];
  if (!sheet) return [];
  const matrix = XLSX.utils.sheet_to_json<(string | number | boolean)[]>(sheet, {
    header: 1,
    defval: "",
    raw: false,
  }) as (string | number | boolean)[][];
  if (matrix.length < 2) return [];
  const headers = matrix[0].map((h) => String(h ?? "").trim());
  const rows: Record<string, string>[] = [];
  for (let i = 1; i < matrix.length; i++) {
    const line = matrix[i];
    if (!line || line.every((c) => String(c ?? "").trim() === "")) continue;
    const row: Record<string, string> = {};
    headers.forEach((h, idx) => {
      if (!h) return;
      row[h] = String(line[idx] ?? "").trim();
    });
    rows.push(row);
  }
  return rows;
}

/** Mapea filas de plantilla (cabeceras en español) a claves internas. */
export function mapImportRows(
  rows: Record<string, string>[],
  columns: ImportColumn[]
): Record<string, string>[] {
  const headerToKey = new Map(columns.map((c) => [c.header.trim().toLowerCase(), c.key]));
  return rows.map((row) => {
    const out: Record<string, string> = {};
    for (const [header, value] of Object.entries(row)) {
      const key = headerToKey.get(header.trim().toLowerCase());
      if (key) out[key] = value;
    }
    return out;
  });
}
