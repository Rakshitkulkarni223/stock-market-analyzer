export default function IndicatorTable({ factors }) {
  try {
    const tag = (s) => (s > 0.5 ? 'pos' : s < -0.5 ? 'neg' : 'neu');
    const barWidth = (s) => Math.min(100, Math.abs(s) * 20);

    return (
      <section className="block">
        <h2>What the indicators say</h2>
        <table>
          <thead>
            <tr>
              <th>Factor</th>
              <th className="num">Reading</th>
              <th className="num">Score</th>
            </tr>
          </thead>
          <tbody>
            {factors.map((f) => (
              <tr key={f.label}>
                <td>
                  <div style={{ fontWeight: 500 }}>{f.label}</div>
                  <span className="sub-note">{f.note}</span>
                </td>
                <td className="num" style={{ fontSize: 12 }}>{f.value}</td>
                <td className="num">
                  <span className={`tag ${tag(f.score)}`}>
                    {f.score > 0 ? '+' : ''}
                    {f.score.toFixed(1)}
                  </span>
                  <div className="score-bar-wrap">
                    <div
                      className={`score-bar ${tag(f.score)}`}
                      style={{ width: `${barWidth(f.score)}%` }}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  } catch (e) {
    return (
      <section className="block">
        <h2>Indicators</h2>
        <div className="sub-note">Error rendering indicators: {e.message}</div>
      </section>
    );
  }
}
