export default function IndicatorTable({ factors }) {
  const tag = (s) => (s > 0.5 ? 'pos' : s < -0.5 ? 'neg' : 'neu');

  return (
    <section className="block">
      <h2>What the indicators read</h2>
      <table>
        <tbody>
          {factors.map((f) => (
            <tr key={f.label}>
              <td>
                {f.label}
                <br />
                <span className="sub-note">{f.note}</span>
              </td>
              <td className="num">{f.value}</td>
              <td className="num">
                <span className={`tag ${tag(f.score)}`}>
                  {f.score > 0 ? '+' : ''}
                  {f.score.toFixed(1)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
