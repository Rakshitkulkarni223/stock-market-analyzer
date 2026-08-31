const POINTS = [
  'Nothing here knows about earnings dates, policy decisions, war, fraud, or a stock being delisted. Price history cannot see the future; it can only describe the past.',
  'The backtest is fitted to the exact window you loaded. A rule that looks strong over two years often falls apart over ten. Change the history length and watch the numbers move \u2014 that instability is the honest signal.',
  'It assumes you get filled at your price with no slippage, and it ignores brokerage, taxes and STT. Real returns come out lower.',
  'Seasonality with 20 or 30 observations is a coincidence more often than a pattern. Read the sample count next to every average.',
  'This is information, not financial advice, and it is not a licensed adviser. For money you cannot afford to lose, talk to a registered investment adviser.',
];

export default function Limits() {
  try {
    return (
      <section className="limits">
        <h2>What this can&rsquo;t tell you</h2>
        <ul>
          {POINTS.map((p) => (
            <li key={p.slice(0, 24)}>{p}</li>
          ))}
        </ul>
      </section>
    );
  } catch (e) {
    return (
      <section className="limits">
        <h2>Limitations</h2>
        <p className="sub-note">Error rendering limitations: {e.message}</p>
      </section>
    );
  }
}
