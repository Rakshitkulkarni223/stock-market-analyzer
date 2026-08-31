import { fmt } from '../api';

export default function LevelsTable({ levels }) {
  try {
    return (
      <section className="block" style={{ marginBottom: 20 }}>
        <h2>Support & Resistance Levels</h2>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th className="num">Price</th>
              <th className="num">Distance</th>
              <th className="num">Tests</th>
            </tr>
          </thead>
          <tbody>
            {levels.map((l) => (
              <tr key={`${l.kind}-${l.price}`}>
                <td>
                  <span
                    className={`tag ${l.kind === 'resistance' ? 'neg' : 'pos'}`}
                    style={{ fontSize: 11 }}
                  >
                    {l.kind === 'resistance' ? 'Resistance' : 'Support'}
                  </span>
                </td>
                <td className="num">{fmt(l.price)}</td>
                <td className={`num ${l.distance_pct > 0 ? 'up' : 'down'}`}>
                  {l.distance_pct > 0 ? '+' : ''}{l.distance_pct.toFixed(1)}%
                </td>
                <td className="num">{l.hits}x</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  } catch (e) {
    return (
      <section className="block">
        <h2>Levels</h2>
        <div className="sub-note">Error rendering levels: {e.message}</div>
      </section>
    );
  }
}
