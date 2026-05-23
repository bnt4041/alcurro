export function formatMoney(cents: number, currency = "EUR"): string {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency,
  }).format(cents / 100);
}

export function parseEurosToCents(value: string): number {
  const n = parseFloat(value.replace(",", "."));
  if (Number.isNaN(n)) return 0;
  return Math.round(n * 100);
}

export function centsToEurosInput(cents: number): string {
  return (cents / 100).toFixed(2);
}
