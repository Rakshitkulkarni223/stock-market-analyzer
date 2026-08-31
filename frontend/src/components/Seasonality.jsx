function Bars({ data }) {
  const max = Math.max(...data.map((d) => Math.abs(d.avg_pct))) || 1;
  return (
    <>
      <div className="bars">
        {data.map((d) => (
          <div key={d.name} title={`${d.avg_pct.toFixed(3)}% average over ${d.n} days`}>
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
            {d.avg_pct.toFixed(2)}
          </span>
        ))}
      </div>
    </>
  );
}

export default function Seasonality({ seasonality }) {
  return (
    <section className="block">
      <h2>When it historically moved</h2>
      <Bars data={seasonality.months} />
      <h3>By weekday</h3>
      <Bars data={seasonality.weekdays} />
      <p className="hint">{seasonality.note}</p>
    </section>
  );
}
