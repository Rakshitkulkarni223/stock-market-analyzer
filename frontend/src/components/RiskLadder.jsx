import { fmt, money } from '../api';

/**
 * The hero of the page: one horizontal price scale running from the stop loss to
 * the stretch target, with the loss side weighted heaviest. The upside is drawn
 * last and lightest on purpose.
 */
export default function RiskLadder({ result }) {
  const { plan, meta, verdict, asset } = result;
  const sym = asset.currency_symbol ?? '';

  const lo = Math.min(plan.stop, plan.entry_low) - (plan.target2 - plan.stop) * 0.06;
  const hi = Math.max(plan.target2, meta.price) + (plan.target2 - plan.stop) * 0.06;
  const span = hi - lo || 1;
  const X = (v) => ((v - lo) / span) * 1000;

  const y = 44;
  const h = 26;

  const Segment = ({ a, b, fill, opacity }) => (
    <rect
      x={X(a).toFixed(1)}
      y={y}
      width={Math.max(0, X(b) - X(a)).toFixed(1)}
      height={h}
      fill={fill}
      opacity={opacity}
    />
  );

  const Marker = ({ v, label, colour, side }) => {
    const x = Math.max(2, Math.min(998, X(v)));
    const anchor = x < 90 ? 'start' : x > 910 ? 'end' : 'middle';
    const up = side === 'up';
    return (
      <g>
        <line x1={x} y1={up ? 32 : y} x2={x} y2={up ? y : y + h + 4} stroke={colour} strokeWidth="1.5" />
        <text
          x={x}
          y={up ? 30 : y + h + 18}
          fill={colour}
          fontSize="12.5"
          fontFamily="IBM Plex Mono, monospace"
          textAnchor={anchor}
        >
          {fmt(v)}
        </text>
        <text
          x={x}
          y={up ? 18 : y + h + 34}
          fill="#93a1a9"
          fontSize="11"
          fontFamily="IBM Plex Sans, sans-serif"
          textAnchor={anchor}
        >
          {label}
        </text>
      </g>
    );
  };

  const rows = [
    ['Buy between', `${fmt(plan.entry_low)} – ${fmt(plan.entry_high)}`, ''],
    ['Exit if it hits', fmt(plan.stop), 'down'],
    ['Risk per unit', `${money(plan.risk_per_unit, sym)} (${plan.risk_pct.toFixed(1)}%)`, 'down'],
    ['First target', `${fmt(plan.target1)}  (${plan.rr1.toFixed(1)}:1)`, 'up'],
    ['Stretch target', `${fmt(plan.target2)}  (${plan.rr2.toFixed(1)}:1)`, 'up'],
    [
      'Setup score',
      `${verdict.score.toFixed(1)} / 10`,
      verdict.score > 2 ? 'up' : verdict.score < -1 ? 'down' : 'flat',
    ],
  ];

  return (
    <section className={`ladder-block ${verdict.tone}`}>
      <div className="verdict">{verdict.headline}</div>
      <p className="verdict-why">{verdict.why}</p>

      <svg
        className="ladder"
        viewBox="0 0 1000 118"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Price ladder: stop ${fmt(plan.stop)}, buy zone ${fmt(plan.entry_low)} to ${fmt(
          plan.entry_high,
        )}, targets ${fmt(plan.target1)} and ${fmt(plan.target2)}`}
      >
        <Segment a={plan.stop} b={plan.entry_low} fill="#c1614a" opacity={0.55} />
        <Segment a={plan.entry_low} b={plan.entry_high} fill="#c9a227" opacity={0.85} />
        <Segment a={plan.entry_high} b={plan.target1} fill="#6e9e7c" opacity={0.32} />
        <Segment a={plan.target1} b={plan.target2} fill="#6e9e7c" opacity={0.55} />
        <rect x="0" y={y} width="1000" height={h} fill="none" stroke="#2c3b44" />
        <Marker v={plan.stop} label="get out here" colour="#c1614a" side="down" />
        <Marker v={plan.entry_low} label="buy zone" colour="#c9a227" side="down" />
        <Marker v={meta.price} label="now" colour="#e9e3d7" side="up" />
        <Marker v={plan.target1} label="first target" colour="#6e9e7c" side="up" />
        <Marker v={plan.target2} label="stretch target" colour="#6e9e7c" side="down" />
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
}
