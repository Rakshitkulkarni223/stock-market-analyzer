import { fmt } from '../api';

export default function LevelsTable({ levels }) {
  return (
    <section className="block" style={{ marginBottom: 18 }}>
      <h2>Levels the price has respected</h2>
      <table>
        <tbody>
          <tr>
            <th>Level</th>
            <th className="num">Price</th>
            <th className="num">Distance</th>
            <th className="num">Times tested</th>
          </tr>
          {levels.map((l) => (
            <tr key={`${l.kind}-${l.price}`}>
              <td>{l.kind === 'resistance' ? 'Resistance' : 'Support'}</td>
              <td className="num">{fmt(l.price)}</td>
              <td className={`num ${l.distance_pct > 0 ? 'up' : 'down'}`}>
                {l.distance_pct.toFixed(1)}%
              </td>
              <td className="num">{l.hits}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
