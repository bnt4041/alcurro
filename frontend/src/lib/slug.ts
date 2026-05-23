/** Código de cuenta: solo minúsculas, números y guiones (para login y URLs). */
export function normalizeAccountCode(raw: string): string {
  return raw
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

export function isValidAccountCode(code: string): boolean {
  return code.length >= 2 && /^[a-z0-9-]+$/.test(code);
}

/** Propuesta de código a partir del nombre comercial o razón social. */
export function suggestAccountCode(name: string, legalName?: string): string {
  const source = name.trim() || legalName?.trim() || "";
  return normalizeAccountCode(source);
}
