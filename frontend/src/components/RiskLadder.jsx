import { fmt, money } from '../api';

/**
 * The hero of the page: one horizontal price scale running from the stop loss to
 * the stretch target, with the loss side weighted heaviest.
 * Supports both long and short directions.
 */
export default function RiskLadder({ result }) {
  try {
    const { plan, meta, verdict, asset, direction } = result;
    const sym = asset.currency_symbol ?? '';
    const isShort = direction === 'short';

    // For the SVG ladder, arrange price scale from lowest to highest
    const allPrices = [plan.stop, plan.entry_low, plan.entry_high, plan.target1, plan.target2, meta.price];
    const minP = Math.min(...allPrices);
    const maxP = Math.max(...allPrices);
    const pad = (maxP - minP) * 0.06;
    const lo = minP - pad;
    const hi = maxP + pad;
    const span = hi - lo || 1;
    const X = (v) => ((v - lo) / span) * 1000;

    const y = 44;
    const h = 28;

    const Segment = ({ a, b, fill, opacity }) => {
      const x1 = X(Math.min(a, b));
      const x2 = X(Math.max(a, b));
      return (
        <rect
          x={x1.toFixed(1)}
          y={y}
          width={Math.max(0, x2 - x1).toFixed(1)}
          height={h}
          fill={fill}
          opacity={opacity}
          rx="4"
        />
      );
    };

    const Marker = ({ v, label, colour, side }) => {
      const x = Math.max(2, Math.min(998, X(v)));
      const anchor = x < 90 ? 'start' : x > 910 ? 'end' : 'middle';
      const up = side === 'up';
      return (
        <g>
          <line
            x1={x} y1={up ? 30 : y}
            x2={x} y2={up ? y : y + h + 4}
            stroke={colour} strokeWidth="2" strokeLinecap="round"
          />
          <text
            x={x} y={up ? 26 : y + h + 20}
            fill={colour} fontSize="13"
            fontFamily="'Inter', 'IBM Plex Mono', monospace"
            fontWeight="600" textAnchor={anchor}
          >
            {fmt(v)}
          </text>
          <text
            x={x} y={up ? 14 : y + h + 36}
            fill="#8b9db0" fontSize="11"
            fontFamily="'Inter', 'IBM Plex Sans', sans-serif"
            textAnchor={anchor}
          >
            {label}
          </text>
        </g>
      );
    };

    const dirLabel = isShort ? 'SHORT' : direction === 'neutral' ? 'NEUTRAL' : 'LONG';

    const rows = isShort ? [
      ['Direction', dirLabel, 'down'],
      ['Short zone', `${fmt(plan.entry_low)} \u2013 ${fmt(plan.entry_high)}`, ''],
      ['Stop loss', `${fmt(plan.stop)} (above entry)`, 'down'],
      ['Risk / unit', `${money(plan.risk_per_unit, sym)} (${plan.risk_pct.toFixed(1)}%)`, 'down'],
      ['Target 1', `${fmt(plan.target1)}  (${plan.rr1.toFixed(1)} : 1)`, 'up'],
      ['Target 2', `${fmt(plan.target2)}  (${plan.rr2.toFixed(1)} : 1)`, 'up'],
      ['Score', `${verdict.score.toFixed(1)} / 10`,
        verdict.score > 2 ? 'up' : verdict.score < -1 ? 'down' : 'flat'],
    ] : [
      ['Direction', dirLabel, direction === 'neutral' ? 'flat' : 'up'],
      ['Buy zone', `${fmt(plan.entry_low)} \u2013 ${fmt(plan.entry_high)}`, ''],
      ['Stop loss', fmt(plan.stop), 'down'],
      ['Risk / unit', `${money(plan.risk_per_unit, sym)} (${plan.risk_pct.toFixed(1)}%)`, 'down'],
      ['Target 1', `${fmt(plan.target1)}  (${plan.rr1.toFixed(1)} : 1)`, 'up'],
      ['Target 2', `${fmt(plan.target2)}  (${plan.rr2.toFixed(1)} : 1)`, 'up'],
      ['Score', `${verdict.score.toFixed(1)} / 10`,
        verdict.score > 2 ? 'up' : verdict.score < -1 ? 'down' : 'flat'],
    ];

    return (
      <section className={`ladder-block ${verdict.tone}`}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span className={`direction-badge ${isShort ? 'short' : direction === 'neutral' ? 'neutral' : 'long'}`}>
            {dirLabel}
          </span>
          <div className="verdict">{verdict.headline}</div>
        </div>
        <p className="verdict-why">{verdict.why}</p>

        <svg
          className="ladder"
          viewBox="0 0 1000 118"
          preserveAspectRatio="none"
          role="img"
          aria-label={`Price ladder: ${isShort ? 'short' : 'buy'} zone ${fmt(plan.entry_low)} to ${fmt(
            plan.entry_high
          )}, stop ${fmt(plan.stop)}, targets ${fmt(plan.target1)} and ${fmt(plan.target2)}`}
        >
          {isShort ? (
            <>
              {/* Short: targets below entry, stop above */}
              <Segment a={plan.target2} b={plan.target1} fill="#22c55e" opacity={0.45} />
              <Segment a={plan.target1} b={plan.entry_low} fill="#22c55e" opacity={0.25} />
              <Segment a={plan.entry_low} b={plan.entry_high} fill="#a855f7" opacity={0.7} />
              <Segment a={plan.entry_high} b={plan.stop} fill="#ef4444" opacity={0.45} />
            </>
          ) : (
            <>
              {/* Long: stop below entry, targets above */}
              <Segment a={plan.stop} b={plan.entry_low} fill="#ef4444" opacity={0.45} />
              <Segment a={plan.entry_low} b={plan.entry_high} fill="#3b82f6" opacity={0.7} />
              <Segment a={plan.entry_high} b={plan.target1} fill="#22c55e" opacity={0.25} />
              <Segment a={plan.target1} b={plan.target2} fill="#22c55e" opacity={0.45} />
            </>
          )}
          <rect x="0" y={y} width="1000" height={h} fill="none" stroke="rgba(255,255,255,0.08)" rx="4" />

          {isShort ? (
            <>
              <Marker v={plan.target2} label="target 2" colour="#4ade80" side="down" />
              <Marker v={plan.target1} label="target 1" colour="#4ade80" side="up" />
              <Marker v={meta.price} label="current" colour="#e8edf2" side="up" />
              <Marker v={plan.entry_high} label="short zone" colour="#c084fc" side="down" />
              <Marker v={plan.stop} label="stop loss" colour="#f87171" side="up" />
            </>
          ) : (
            <>
              <Marker v={plan.stop} label="stop loss" colour="#f87171" side="down" />
              <Marker v={plan.entry_low} label="buy zone" colour="#60a5fa" side="down" />
              <Marker v={meta.price} label="current" colour="#e8edf2" side="up" />
              <Marker v={plan.target1} label="target 1" colour="#4ade80" side="up" />
              <Marker v={plan.target2} label="target 2" colour="#4ade80" side="down" />
            </>
          )}
        </svg>

        <dl className="rr">
          {rows.map(([k, v, cls]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd className={cls}>{v}</dd>
            </div>
          ))}
        </dl>
      </section>
    );
  } catch (e) {
    return (
      <section className="ladder-block neutral">
        <div className="verdict">Error</div>
        <p className="verdict-why">Could not render risk ladder: {e.message}</p>
      </section>
    );
  }
}
