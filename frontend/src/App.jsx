import { useCallback, useEffect, useRef, useState } from 'react';

import { analyse, analyseCsv, getUniverse } from './api';
import AssetPicker from './components/AssetPicker';
import BacktestPanel from './components/BacktestPanel';
import IndicatorTable from './components/IndicatorTable';
import LevelsTable from './components/LevelsTable';
import Limits from './components/Limits';
import PositionSizer from './components/PositionSizer';
import PriceChart from './components/PriceChart';
import RiskLadder from './components/RiskLadder';
import Seasonality from './components/Seasonality';
import Ticker from './components/Ticker';

export default function App() {
  const [universe, setUniverse] = useState(null);
  const [selected, setSelected] = useState(null);
  const [range, setRange] = useState('2y');
  const [style, setStyle] = useState('swing');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ message: 'Nothing loaded yet.', error: false });
  const inflight = useRef(null);

  useEffect(() => {
    try {
      getUniverse()
        .then((u) => {
          setUniverse(u);
          setSelected(u.categories[0]?.assets[0] ?? null);
        })
        .catch((e) =>
          setStatus({
            message: `Cannot reach the backend (${e.message}). Start it with: uvicorn app.main:app --reload`,
            error: true,
          }),
        );
    } catch (e) {
      setStatus({ message: `Unexpected error: ${e.message}`, error: true });
    }
  }, []);

  const start = () => {
    try {
      inflight.current?.abort();
      inflight.current = new AbortController();
      setLoading(true);
      return inflight.current.signal;
    } catch (e) {
      setLoading(false);
      return null;
    }
  };

  const finish = (data, message) => {
    try {
      setResult(data);
      setStatus({ message, error: false });
      setLoading(false);
    } catch (e) {
      setStatus({ message: `Error processing result: ${e.message}`, error: true });
      setLoading(false);
    }
  };

  const fail = (e) => {
    try {
      if (e.name === 'AbortError') return;
      setStatus({ message: e.message, error: true });
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  };

  const runSymbol = useCallback(
    (asset, opts = {}) => {
      try {
        const target = asset ?? selected;
        if (!target) return;
        const rng = opts.range ?? range;
        const sty = opts.style ?? style;
        const signal = start();
        setStatus({ message: `Loading ${target.name}...`, error: false });
        analyse({ symbol: target.symbol, source: target.source, range: rng, style: sty }, signal)
          .then((d) => finish(d, `${d.meta.bars} daily bars loaded from ${d.asset.source}.`))
          .catch(fail);
      } catch (e) {
        fail(e);
      }
    },
    [range, style, selected],
  );

  const runCsv = useCallback(
    ({ file, text, label }) => {
      try {
        const signal = start();
        setStatus({ message: 'Parsing your file...', error: false });
        analyseCsv({ file, text, style, label }, signal)
          .then((d) => finish(d, `${d.meta.bars} bars parsed from your data.`))
          .catch(fail);
      } catch (e) {
        fail(e);
      }
    },
    [style],
  );

  const onSelect = (asset) => {
    try {
      setSelected(asset);
      runSymbol(asset);
    } catch (e) {
      fail(e);
    }
  };

  const onRange = (r) => {
    try {
      setRange(r);
      if (result && result.asset.source !== 'csv') runSymbol(selected, { range: r });
    } catch (e) {
      fail(e);
    }
  };

  const onStyle = (s) => {
    try {
      setStyle(s);
      if (result && result.asset.source !== 'csv') runSymbol(selected, { style: s });
    } catch (e) {
      fail(e);
    }
  };

  return (
    <div className="wrap">
      <header className="masthead">
        <h1>Know the downside before you look at the upside.</h1>
        <p>
          Pick a market. This reads its price history and hands you three numbers that matter: where
          to buy, where you get out if you&rsquo;re wrong, and how many units keep that mistake
          survivable.
        </p>
        <div className="caution">
          No tool can promise you won&rsquo;t lose money &mdash; anyone who says otherwise is selling
          something. What a plan can do is cap the loss on any single trade to an amount you chose in
          advance.
        </div>
      </header>

      <div className="desk">
        <aside className="rail">
          <AssetPicker
            universe={universe}
            selected={selected}
            onSelect={onSelect}
            range={range}
            setRange={onRange}
            style={style}
            setStyle={onStyle}
            onRun={() => runSymbol(selected)}
            onCsv={runCsv}
            loading={loading}
            status={status}
          />
        </aside>

        <main>
          {!result ? (
            <div className="empty">
              Pick a market on the left and press Analyse to get started.
            </div>
          ) : (
            <>
              {result.meta.thin_history && (
                <div className="banner">
                  Only {result.meta.bars} bars of history. The long-term averages and level
                  detection need more than that &mdash; load at least a year before trusting any
                  number below.
                </div>
              )}

              <Ticker result={result} />
              <RiskLadder result={result} />

              <div className="section-divider">Price Action</div>
              <PriceChart result={result} />

              <div className="section-divider">Position & Analysis</div>
              <div className="cols">
                <PositionSizer result={result} />
                <IndicatorTable factors={result.factors} />
              </div>

              <div className="section-divider">Historical Performance</div>
              <div className="cols">
                <BacktestPanel backtest={result.backtest} bars={result.meta.bars} />
                <Seasonality seasonality={result.seasonality} />
              </div>

              <div className="section-divider">Key Levels</div>
              <LevelsTable levels={result.levels} />
              <Limits />
            </>
          )}

          <footer>
            Built for your own research. Prices are fetched server-side, so no browser CORS limits
            apply and no API keys are needed. Nothing is stored and no orders are ever placed.
          </footer>
        </main>
      </div>
    </div>
  );
}
