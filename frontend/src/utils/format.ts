export function formatCurrency(value: number): string {
  if (value === null || value === undefined) return '¥0.00';
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatCurrencyShort(value: number): string {
  if (value === null || value === undefined) return '¥0';
  if (Math.abs(value) >= 100000) return `¥${(value / 10000).toFixed(1)}万`;
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export function formatNumber(value: number): string {
  if (value === null || value === undefined) return '0';
  return value.toLocaleString('zh-CN');
}

export function formatPercent(value: number): string {
  if (value === null || value === undefined) return '0.00%';
  return `${value.toFixed(2)}%`;
}

export function formatQty(value: number): string {
  if (value === null || value === undefined) return '0';
  return value.toLocaleString('zh-CN');
}
