import { signed } from '../api';

export default function BacktestPanel({ backtest, bars }) {
  try {
    const b = backtest;
    const tone = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : '');

    const rows = [
      ['Trades taken', String(b.trades), ''],
      ['Win rate', `${b.win_rate.toFixed(0)}%`, b.win_rate >= 45 ? 'up' : 'down'],
      ['Average win', signed(b.avg_win), 'up'],
      ['Average loss', signed(b.avg_loss), 'down'],
      ['Expected per trade', signed(b.expectancy), tone(b.expectancy)],
      ['Compounded return', signed(b.net_return), tone(b.net_return)],
      ['Buy & hold return', signed(b.buy_hold_return), tone(b.buy_hold_return)],
      ['Max drawdown', `${b.max_drawdown.toFixed(1)}%`, 'down'],
      ['Avg holding period', `${b.avg_bars_held} bars`, ''],
      ['Stopped out', `${b.stopped_out} / ${b.trades}`, ''],
    ];

    return (
      <section className="block">
        <h2>Did this rule work?</h2>
        <p className="sub-note" style={{ margin: '0 0 14px' }}>
          {b.rule} Tested over {bars} bars.
        </p>
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th className="num">Value</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([k, v, cls]) => (
              <tr key={k}>
                <td>{k}</td>
                <td className={`num ${cls}`}>{v}</td>
              </tr>
            ))}
            <tr>
              <td colSpan={2} className="sub-note" style={{ paddingTop: 12 }}>
                {b.note}
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    );
  } catch (e) {
    return (
      <section className="block">
        <h2>Backtest</h2>
        <div className="sub-note">Error rendering backtest: {e.message}</div>
      </section>
    );
  }
}
