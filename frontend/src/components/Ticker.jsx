import { fmt, money, shortDate } from '../api';

export default function Ticker({ result }) {
  try {
    const { meta, asset, direction } = result;
    const change = meta.change_pct;
    const cls = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
    const isShort = direction === 'short';
    const dirLabel = isShort ? 'SHORT' : direction === 'neutral' ? 'NEUTRAL' : 'LONG';

    return (
      <div className="tickline">
        <span className="name">{asset.name}</span>
        <span className="px">{money(meta.price, asset.currency_symbol)}</span>
        <span className={`chg ${cls}`}>
          {change >= 0 ? '+' : ''}
          {change.toFixed(2)}%
        </span>
        <span className={`direction-badge-sm ${isShort ? 'short' : direction === 'neutral' ? 'neutral' : 'long'}`}>
          {dirLabel}
        </span>
        <span className="meta">
          {meta.bars} bars &middot; {shortDate(asset.first_bar)} &ndash;{' '}
          {shortDate(asset.last_bar)} &middot; ATR {fmt(meta.atr)} ({meta.atr_pct.toFixed(2)}%)
        </span>
      </div>
    );
  } catch (e) {
    return <div className="sub-note">Error rendering ticker: {e.message}</div>;
  }
}
