const BASE = import.meta.env.VITE_API_BASE || '/api';

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function unwrap(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error page */
  }
  if (!res.ok) {
    const detail = body?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join('; ')
          : `Request failed with status ${res.status}`;
    throw new ApiError(message, res.status);
  }
  return body;
}

export async function getUniverse() {
  return unwrap(await fetch(`${BASE}/universe`));
}

export async function analyse({ symbol, source, range, style }, signal) {
  const qs = new URLSearchParams({ symbol, range, style });
  if (source) qs.set('source', source);
  return unwrap(await fetch(`${BASE}/analyse?${qs}`, { signal }));
}

export async function analyseCsv({ file, text, style, label }, signal) {
  const form = new FormData();
  if (file) form.append('file', file);
  if (text) form.append('text', text);
  form.append('style', style);
  if (label) form.append('label', label);
  return unwrap(await fetch(`${BASE}/analyse/csv`, { method: 'POST', body: form, signal }));
}

export async function positionSize(body, signal) {
  return unwrap(
    await fetch(`${BASE}/position-size`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    }),
  );
}

/* ---------------------------------------------------------------- formatting */

export function fmt(x) {
  if (x === null || x === undefined || !Number.isFinite(x)) return '—';
  const a = Math.abs(x);
  const d = a >= 1000 ? 0 : a >= 10 ? 2 : a >= 1 ? 3 : 5;
  return x.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
}

export function money(x, symbol = '') {
  return `${symbol}${fmt(x)}`;
}

export function signed(x, digits = 2) {
  if (!Number.isFinite(x)) return '—';
  return `${x >= 0 ? '+' : ''}${x.toFixed(digits)}%`;
}

export function shortDate(ms) {
  return new Date(ms).toLocaleDateString();
}

export { ApiError };
