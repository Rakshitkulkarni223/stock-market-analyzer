import { fmt, money, shortDate } from '../api';

export default function Ticker({ result }) {
  try {
    const { meta, asset, direction } = result;
    const change = meta.change_pct;
    const cls = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
    const isShort = direction === 'short';
    const dirLabel = isShort ? 'SHORT' : direction === 'neutral' ? 'NEUTRAL' : 'LONG';

    return (
      <section className="stat-strip">
        <div className="stat-strip-id">
          <span className="name">{asset.name}</span>
          <span className="ticker-sym">{asset.symbol}</span>
        </div>

        <div className="stat-strip-price">
          <span className="px">{money(meta.price, asset.currency_symbol)}</span>
          <span className={`chg ${cls}`}>
            {change >= 0 ? '+' : ''}
            {change.toFixed(2)}%
          </span>
        </div>

        <span className={`direction-badge-sm ${isShort ? 'short' : direction === 'neutral' ? 'neutral' : 'long'}`}>
          {dirLabel}
        </span>

        <div className="stat-strip-meta">
          <dl className="stat">
            <dt>History</dt>
            <dd>
              {meta.bars} bars &middot; {shortDate(asset.first_bar)}&ndash;{shortDate(asset.last_bar)}
            </dd>
          </dl>
          <dl className="stat">
            <dt>ATR (14)</dt>
            <dd>
              {fmt(meta.atr)} <span className="sub-note">({meta.atr_pct.toFixed(2)}%)</span>
            </dd>
          </dl>
        </div>
      </section>
    );
  } catch (e) {
    return <div className="sub-note">Error rendering ticker: {e.message}</div>;
  }
}
