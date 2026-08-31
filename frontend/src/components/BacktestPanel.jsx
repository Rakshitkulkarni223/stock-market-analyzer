import { signed } from '../api';

export default function BacktestPanel({ backtest, bars }) {
  const b = backtest;
  const tone = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : '');

  const rows = [
    ['Trades taken', String(b.trades), ''],
    ['Win rate', `${b.win_rate.toFixed(0)}%`, b.win_rate >= 45 ? 'up' : 'down'],
    ['Average win', signed(b.avg_win), 'up'],
    ['Average loss', signed(b.avg_loss), 'down'],
    ['Expected result per trade', signed(b.expectancy), tone(b.expectancy)],
    ['Compounded over the window', signed(b.net_return), tone(b.net_return)],
    ['Buy and hold, same window', signed(b.buy_hold_return), tone(b.buy_hold_return)],
    ['Worst peak-to-trough drop', `−${b.max_drawdown.toFixed(1)}%`, 'down'],
    ['Average holding period', `${b.avg_bars_held} bars`, ''],
    ['Trades stopped out', `${b.stopped_out} of ${b.trades}`, ''],
  ];

  return (
    <section className="block">
      <h2>Did this rule actually work here?</h2>
      <p className="sub-note" style={{ margin: '0 0 12px', fontSize: 13.5 }}>
        {b.rule} Run over the {bars} bars you loaded.
      </p>
      <table>
        <tbody>
          {rows.map(([k, v, cls]) => (
            <tr key={k}>
              <td>{k}</td>
              <td className={`num ${cls}`}>{v}</td>
            </tr>
          ))}
          <tr>
            <td colSpan={2} className="sub-note" style={{ paddingTop: 10 }}>
              {b.note}
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}
