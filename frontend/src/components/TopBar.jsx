import { useEffect, useRef, useState } from 'react';
import AssetPicker from './AssetPicker';

/**
 * App chrome: brand, the symbol switcher (opens the full market picker in a
 * dropdown rather than pinning it to the page as a permanent sidebar), and a
 * tucked-away disclaimer. Keeps all picking/range/style/CSV logic inside
 * AssetPicker untouched — this just changes where it lives on screen.
 */
export default function TopBar({
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
  const [open, setOpen] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const boxRef = useRef(null);
  const infoRef = useRef(null);

  useEffect(() => {
    if (!open && !infoOpen) return undefined;
    const onDown = (e) => {
      if (open && boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
      if (infoOpen && infoRef.current && !infoRef.current.contains(e.target)) setInfoOpen(false);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        setInfoOpen(false);
      }
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, infoOpen]);

  const handleSelect = (asset) => {
    try {
      onSelect(asset);
    } finally {
      setOpen(false);
    }
  };

  const handleRun = () => {
    try {
      onRun();
    } finally {
      setOpen(false);
    }
  };

  const handleCsv = (payload) => {
    try {
      onCsv(payload);
    } finally {
      setOpen(false);
    }
  };

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            MD
          </span>
          <div className="brand-text">
            <span className="brand-name">Market Desk</span>
            <span className="brand-tagline">Risk before reward</span>
          </div>
        </div>

        <div className="symbol-box" ref={boxRef}>
          <button
            type="button"
            className="symbol-switch"
            aria-expanded={open}
            aria-haspopup="true"
            onClick={() => setOpen((v) => !v)}
            disabled={!universe}
          >
            {selected ? (
              <>
                <span className="symbol-switch-name">{selected.name}</span>
                <span className="symbol-switch-ticker">{selected.symbol.replace('USDT', '')}</span>
              </>
            ) : (
              <span className="symbol-switch-name">
                {universe ? 'Choose a market' : 'Loading markets…'}
              </span>
            )}
            <svg className={`chev${open ? ' up' : ''}`} width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
              <path
                d="M1 3 L5 7 L9 3"
                stroke="currentColor"
                strokeWidth="1.6"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>

          {open && (
            <div className="picker-dropdown" role="dialog" aria-label="Choose a market">
              <AssetPicker
                universe={universe}
                selected={selected}
                onSelect={handleSelect}
                range={range}
                setRange={setRange}
                style={style}
                setStyle={setStyle}
                onRun={handleRun}
                onCsv={handleCsv}
                loading={loading}
                status={status}
              />
            </div>
          )}
        </div>

        <div className="topbar-spacer" />

        <div className="topbar-status" aria-live="polite">
          {loading ? (
            <span className="status-pill loading">Analysing&hellip;</span>
          ) : status?.error ? (
            <span className="status-pill err">{status.message}</span>
          ) : null}
        </div>

        <div className="info-box" ref={infoRef}>
          <button
            type="button"
            className="icon-btn"
            aria-expanded={infoOpen}
            aria-label="About this tool and its risk disclaimer"
            onClick={() => setInfoOpen((v) => !v)}
          >
            i
          </button>
          {infoOpen && (
            <div className="info-pop" role="dialog" aria-label="About Market Desk">
              <p>
                Pick a market. This reads its price history and hands you three numbers that
                matter: where to buy, where you get out if you&rsquo;re wrong, and how many units
                keep that mistake survivable.
              </p>
              <p className="info-caution">
                No tool can promise you won&rsquo;t lose money &mdash; anyone who says otherwise is
                selling something. What a plan can do is cap the loss on any single trade to an
                amount you chose in advance.
              </p>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
