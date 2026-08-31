function Bars({ data }) {
  try {
    const max = Math.max(...data.map((d) => Math.abs(d.avg_pct))) || 1;
    return (
      <>
        <div className="bars">
          {data.map((d) => (
            <div key={d.name} title={`${d.avg_pct.toFixed(3)}% avg over ${d.n} days`}>
              <b
                className={d.avg_pct < 0 ? 'neg' : undefined}
                style={{ height: `${((Math.abs(d.avg_pct) / max) * 100).toFixed(0)}%` }}
              />
            </div>
          ))}
        </div>
        <div className="barlabels">
          {data.map((d) => (
            <span key={d.name}>
              {d.name}
              <br />
              <span style={{ color: d.avg_pct >= 0 ? 'var(--green-text)' : 'var(--red-text)' }}>
                {d.avg_pct >= 0 ? '+' : ''}{d.avg_pct.toFixed(2)}%
              </span>
            </span>
          ))}
        </div>
      </>
    );
  } catch (e) {
    return <div className="sub-note">Error rendering bars: {e.message}</div>;
  }
}

export default function Seasonality({ seasonality }) {
  try {
    return (
      <section className="block">
        <h2>Seasonal patterns</h2>
        <h3>Monthly</h3>
        <Bars data={seasonality.months} />
        <h3>By weekday</h3>
        <Bars data={seasonality.weekdays} />
        <p className="hint">{seasonality.note}</p>
      </section>
    );
  } catch (e) {
    return (
      <section className="block">
        <h2>Seasonality</h2>
        <div className="sub-note">Error rendering seasonality: {e.message}</div>
      </section>
    );
  }
}
