import { fmt, money, shortDate } from '../api';

export default function Ticker({ result }) {
  const { meta, asset } = result;
  const change = meta.change_pct;
  const cls = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';

  return (
    <div className="tickline">
      <span className="name">{asset.name}</span>
      <span className="px">{money(meta.price, asset.currency_symbol)}</span>
      <span className={`chg ${cls}`}>
        {change >= 0 ? '+' : ''}
        {change.toFixed(2)}% on the day
      </span>
      <span className="meta">
        {meta.bars} bars · {shortDate(asset.first_bar)} to {shortDate(asset.last_bar)} · ATR{' '}
        {fmt(meta.atr)} ({meta.atr_pct.toFixed(2)}%)
      </span>
    </div>
  );
}
