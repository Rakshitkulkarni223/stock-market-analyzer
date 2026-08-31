import { useEffect, useState } from 'react';
import { money, positionSize } from '../api';

/**
 * Deliberately calls the backend rather than duplicating the arithmetic here:
 * the concentration warnings are a risk rule, and a risk rule should have exactly
 * one implementation.
 */
export default function PositionSizer({ result }) {
  try {
    const { plan, asset, direction } = result;
    const sym = asset.currency_symbol ?? '';
    const isShort = direction === 'short';
    const [capital, setCapital] = useState(100000);
    const [riskPct, setRiskPct] = useState(1);
    const [size, setSize] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
      try {
        if (!capital || capital <= 0 || !riskPct || riskPct <= 0) {
          setSize(null);
          return undefined;
        }
        const controller = new AbortController();
        const timer = setTimeout(() => {
          positionSize(
            {
              capital: Number(capital),
              risk_pct: Number(riskPct),
              entry: plan.entry_mid,
              stop: plan.stop,
              target: plan.target1,
              direction: direction || 'long',
            },
            controller.signal,
          )
            .then((d) => {
              setSize(d);
              setError(null);
            })
            .catch((e) => {
              if (e.name !== 'AbortError') setError(e.message);
            });
        }, 300);
        return () => {
          clearTimeout(timer);
          controller.abort();
        };
      } catch (e) {
        setError(e.message);
        return undefined;
      }
    }, [capital, riskPct, plan, direction]);

    const actionLabel = isShort ? 'How much to short' : 'How much to buy';
    const entryLabel = isShort ? 'short at' : 'buy at';

    return (
      <section className="block">
        <h2>{actionLabel}</h2>

        <div className="row">
          <div className="field">
            <label htmlFor="capital">Total capital</label>
            <input
              id="capital"
              type="number"
              min="0"
              step="1000"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="riskpct">Risk per trade (%)</label>
            <input
              id="riskpct"
              type="number"
              min="0.1"
              max="20"
              step="0.1"
              value={riskPct}
              onChange={(e) => setRiskPct(e.target.value)}
            />
          </div>
        </div>

        <div className="calc-out">
          {error && <div className="warnline">{error}</div>}
          {!error && !size && <div className="spinner">Calculating...</div>}
          {!error && size && (
            <>
              <span className="big">{size.units.toLocaleString()} units</span>
              <span className="sub">
                {entryLabel} ~{money(plan.entry_mid, sym)} &mdash;{' '}
                {money(size.position_value, sym)} committed ({size.capital_share_pct.toFixed(1)}%
                of capital)
              </span>
              <div className="calc-split">
                <div>
                  If stopped:{' '}
                  <strong className="down">&minus;{money(size.loss_if_stopped, sym)}</strong>{' '}
                  ({size.loss_pct_of_capital.toFixed(2)}% of capital)
                </div>
                <div>
                  If target hit:{' '}
                  <strong className="up">+{money(size.gain_if_target, sym)}</strong>
                </div>
              </div>
              {size.warning && <div className="warnline">{size.warning}</div>}
            </>
          )}
        </div>

        <p className="hint">
          1% risk per trade means ten straight losses cost ~10% of your account, not all of it.
          This is the single biggest lever you control.
        </p>
      </section>
    );
  } catch (e) {
    return (
      <section className="block">
        <h2>Position Sizing</h2>
        <div className="sub-note">Error: {e.message}</div>
      </section>
    );
  }
}
