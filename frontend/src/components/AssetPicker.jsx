import { useMemo, useRef, useState } from 'react';

export default function AssetPicker({
  universe,
  selected,
  onSelect,
  range,
  setRange,
  style,
  setStyle,
  onRun,
  onCsv,
  loading,
  status,
}) {
  const categories = universe?.categories ?? [];
  const [cat, setCat] = useState(categories[0]?.name ?? '');
  const [query, setQuery] = useState('');
  const [csvOpen, setCsvOpen] = useState(false);
  const [csvText, setCsvText] = useState('');
  const fileRef = useRef(null);

  const activeCat = cat || categories[0]?.name;

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return categories.find((c) => c.name === activeCat)?.assets ?? [];
    return categories
      .flatMap((c) => c.assets)
      .filter((a) => `${a.name} ${a.symbol}`.toLowerCase().includes(q));
  }, [query, activeCat, categories]);

  const rangeLabels = {
    '6mo': '6 months',
    '1y': '1 year',
    '2y': '2 years',
    '5y': '5 years',
    '10y': '10 years',
    max: 'Everything',
  };

  return (
    <div className="block">
      <h2>Choose a market</h2>

      <div className="cats">
        {categories.map((c) => (
          <button
            key={c.name}
            type="button"
            className="cat"
            aria-pressed={c.name === activeCat}
            onClick={() => {
              setCat(c.name);
              setQuery('');
            }}
          >
            {c.name}
          </button>
        ))}
      </div>

      <input
        type="text"
        placeholder="Search name or ticker"
        value={query}
        autoComplete="off"
        onChange={(e) => setQuery(e.target.value)}
      />

      <div className="assets">
        {visible.length === 0 ? (
          <div className="asset-empty">
            Nothing matches that. Try a shorter word, or import a CSV.
          </div>
        ) : (
          visible.map((a) => (
            <button
              key={a.symbol}
              type="button"
              className="asset"
              aria-pressed={selected?.symbol === a.symbol}
              onClick={() => onSelect(a)}
            >
              <span>{a.name}</span>
              <span>{a.symbol.replace('USDT', '')}</span>
            </button>
          ))
        )}
      </div>

      <div className="row">
        <div className="field">
          <label htmlFor="range">History</label>
          <select id="range" value={range} onChange={(e) => setRange(e.target.value)}>
            {(universe?.ranges ?? ['2y']).map((r) => (
              <option key={r} value={r}>
                {rangeLabels[r] ?? r}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="style">Holding style</label>
          <select id="style" value={style} onChange={(e) => setStyle(e.target.value)}>
            {(universe?.styles ?? [{ id: 'swing', label: 'Swing' }]).map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button className="go" type="button" onClick={onRun} disabled={loading || !selected}>
        {loading ? 'Reading the history…' : 'Analyse'}
      </button>

      <button className="ghost" type="button" onClick={() => setCsvOpen((v) => !v)}>
        {csvOpen ? 'Hide CSV import' : 'Import prices from a CSV instead'}
      </button>

      <div className={`status${status?.error ? ' err' : ''}`}>{status?.message}</div>

      {csvOpen && (
        <div style={{ marginTop: 14 }}>
          <h3>Paste or upload daily price history</h3>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.txt"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onCsv({ file: f, label: f.name });
            }}
          />
          <textarea
            placeholder={'Date,Open,High,Low,Close,Volume\n2024-01-01,100,102,99,101,120000\n…'}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
          />
          <button
            className="ghost"
            type="button"
            disabled={!csvText.trim() || loading}
            onClick={() => onCsv({ text: csvText })}
          >
            Analyse this data
          </button>
          <p className="hint">
            Works with the CSV that Yahoo Finance, NSE or Investing.com give you when you download
            historical data. Oldest or newest row first — either is fine.
          </p>
        </div>
      )}
    </div>
  );
}
