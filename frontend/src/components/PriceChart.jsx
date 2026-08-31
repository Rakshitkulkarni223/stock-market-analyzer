import { useCallback, useEffect, useRef, useState } from 'react';
import { fmt } from '../api';

const COLOURS = {
  grid: '#243139',
  axis: '#6b7b84',
  up: '#6e9e7c',
  down: '#c1614a',
  sma20: '#c9a227',
  sma50: '#5b8ca8',
  sma200: '#9b7bb8',
  band: 'rgba(91,140,168,.10)',
  zone: 'rgba(201,162,39,.16)',
};

function ctx2d(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = Math.max(1, Math.round(w * dpr));
  canvas.height = Math.max(1, Math.round(h * dpr));
  const g = canvas.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  return { g, w, h };
}

export default function PriceChart({ result }) {
  const priceRef = useRef(null);
  const rsiRef = useRef(null);
  const macdRef = useRef(null);
  const geomRef = useRef(null);
  const [hover, setHover] = useState(null);

  const s = result.series;
  const plan = result.plan;
  const n = s.c.length;

  const drawPrice = useCallback(() => {
    const cv = priceRef.current;
    if (!cv) return;
    const { g, w, h } = ctx2d(cv);
    const PL = 8;
    const PR = 68;
    const PT = 10;
    const PB = 22;
    const iw = w - PL - PR;
    const ih = h - PT - PB;

    let lo = Infinity;
    let hi = -Infinity;
    for (let i = 0; i < n; i += 1) {
      if (s.l[i] != null) lo = Math.min(lo, s.l[i]);
      if (s.h[i] != null) hi = Math.max(hi, s.h[i]);
      if (s.bb_lower[i] != null) lo = Math.min(lo, s.bb_lower[i]);
      if (s.bb_upper[i] != null) hi = Math.max(hi, s.bb_upper[i]);
    }
    lo = Math.min(lo, plan.stop);
    hi = Math.max(hi, plan.target2);
    const pad = (hi - lo) * 0.04;
    lo -= pad;
    hi += pad;

    const X = (i) => PL + (i / Math.max(1, n - 1)) * iw;
    const Y = (v) => PT + (1 - (v - lo) / (hi - lo)) * ih;

    g.font = '11px "IBM Plex Mono", monospace';
    g.textBaseline = 'middle';
    for (let k = 0; k <= 5; k += 1) {
      const v = lo + ((hi - lo) * k) / 5;
      const yy = Y(v);
      g.strokeStyle = COLOURS.grid;
      g.lineWidth = 1;
      g.beginPath();
      g.moveTo(PL, yy);
      g.lineTo(PL + iw, yy);
      g.stroke();
      g.fillStyle = COLOURS.axis;
      g.textAlign = 'left';
      g.fillText(fmt(v), PL + iw + 7, yy);
    }

    // Bollinger envelope
    g.beginPath();
    let started = false;
    for (let i = 0; i < n; i += 1) {
      if (s.bb_upper[i] == null) continue;
      if (started) g.lineTo(X(i), Y(s.bb_upper[i]));
      else {
        g.moveTo(X(i), Y(s.bb_upper[i]));
        started = true;
      }
    }
    for (let i = n - 1; i >= 0; i -= 1) {
      if (s.bb_lower[i] == null) continue;
      g.lineTo(X(i), Y(s.bb_lower[i]));
    }
    g.closePath();
    g.fillStyle = COLOURS.band;
    g.fill();

    // plan zone + levels
    g.fillStyle = COLOURS.zone;
    g.fillRect(PL, Y(plan.entry_high), iw, Math.max(2, Y(plan.entry_low) - Y(plan.entry_high)));
    const hline = (v, colour, dash) => {
      g.save();
      g.setLineDash(dash);
      g.strokeStyle = colour;
      g.lineWidth = 1.3;
      g.beginPath();
      g.moveTo(PL, Y(v));
      g.lineTo(PL + iw, Y(v));
      g.stroke();
      g.restore();
    };
    hline(plan.stop, COLOURS.down, [5, 4]);
    hline(plan.target1, COLOURS.up, [5, 4]);
    hline(plan.target2, COLOURS.up, [2, 5]);

    // candles
    const cw = Math.max(1, Math.min(9, (iw / n) * 0.68));
    for (let i = 0; i < n; i += 1) {
      if (s.c[i] == null) continue;
      const rising = s.c[i] >= s.o[i];
      const colour = rising ? COLOURS.up : COLOURS.down;
      g.strokeStyle = colour;
      g.lineWidth = 1;
      g.beginPath();
      g.moveTo(X(i), Y(s.h[i]));
      g.lineTo(X(i), Y(s.l[i]));
      g.stroke();
      const yo = Y(s.o[i]);
      const yc = Y(s.c[i]);
      g.fillStyle = colour;
      g.fillRect(X(i) - cw / 2, Math.min(yo, yc), cw, Math.max(1, Math.abs(yc - yo)));
    }

    const line = (arr, colour, lw) => {
      g.strokeStyle = colour;
      g.lineWidth = lw;
      g.beginPath();
      let open = false;
      for (let i = 0; i < n; i += 1) {
        if (arr[i] == null) continue;
        if (open) g.lineTo(X(i), Y(arr[i]));
        else {
          g.moveTo(X(i), Y(arr[i]));
          open = true;
        }
      }
      g.stroke();
    };
    line(s.sma200, COLOURS.sma200, 1.6);
    line(s.sma50, COLOURS.sma50, 1.4);
    line(s.sma20, COLOURS.sma20, 1.4);

    g.fillStyle = COLOURS.axis;
    g.textAlign = 'center';
    g.textBaseline = 'top';
    for (let k = 0; k <= 4; k += 1) {
      const i = Math.round(((n - 1) * k) / 4);
      const d = new Date(s.t[i]);
      g.fillText(
        d.toLocaleDateString(undefined, { month: 'short', year: '2-digit' }),
        X(i),
        PT + ih + 6,
      );
    }

    geomRef.current = { PL, iw };
  }, [n, plan, s]);

  const drawSub = useCallback(
    (ref, arr, opts) => {
      const cv = ref.current;
      if (!cv) return;
      const { g, w, h } = ctx2d(cv);
      const PL = 8;
      const PR = 68;
      const PT = 6;
      const PB = 6;
      const iw = w - PL - PR;
      const ih = h - PT - PB;

      let lo = opts.lo;
      let hi = opts.hi;
      if (lo == null) {
        lo = Infinity;
        hi = -Infinity;
        for (let i = 0; i < n; i += 1) {
          if (arr[i] == null) continue;
          lo = Math.min(lo, arr[i]);
          hi = Math.max(hi, arr[i]);
        }
        const m = (hi - lo) * 0.12 || 1;
        lo -= m;
        hi += m;
      }
      const X = (i) => PL + (i / Math.max(1, n - 1)) * iw;
      const Y = (v) => PT + (1 - (v - lo) / (hi - lo)) * ih;

      g.font = '10.5px "IBM Plex Mono", monospace';
      g.textBaseline = 'middle';
      g.textAlign = 'left';
      (opts.guides ?? []).forEach((gd) => {
        g.save();
        g.setLineDash(gd.dash ?? [3, 4]);
        g.strokeStyle = gd.colour;
        g.lineWidth = 1;
        g.beginPath();
        g.moveTo(PL, Y(gd.v));
        g.lineTo(PL + iw, Y(gd.v));
        g.stroke();
        g.restore();
        g.fillStyle = COLOURS.axis;
        g.fillText(String(gd.v), PL + iw + 7, Y(gd.v));
      });

      if (opts.bars) {
        const cw = Math.max(1, Math.min(7, (iw / n) * 0.7));
        for (let i = 0; i < n; i += 1) {
          if (arr[i] == null) continue;
          g.fillStyle = arr[i] >= 0 ? 'rgba(110,158,124,.85)' : 'rgba(193,97,74,.85)';
          const y0 = Y(0);
          const y1 = Y(arr[i]);
          g.fillRect(X(i) - cw / 2, Math.min(y0, y1), cw, Math.max(1, Math.abs(y1 - y0)));
        }
      } else {
        g.strokeStyle = opts.colour;
        g.lineWidth = 1.5;
        g.beginPath();
        let open = false;
        for (let i = 0; i < n; i += 1) {
          if (arr[i] == null) continue;
          if (open) g.lineTo(X(i), Y(arr[i]));
          else {
            g.moveTo(X(i), Y(arr[i]));
            open = true;
          }
        }
        g.stroke();
      }
    },
    [n],
  );

  const drawAll = useCallback(() => {
    drawPrice();
    drawSub(rsiRef, s.rsi, {
      lo: 0,
      hi: 100,
      colour: COLOURS.sma20,
      guides: [
        { v: 70, colour: COLOURS.down },
        { v: 50, colour: COLOURS.grid },
        { v: 30, colour: COLOURS.up },
      ],
    });
    drawSub(macdRef, s.macd_hist, {
      bars: true,
      guides: [{ v: 0, colour: COLOURS.grid, dash: [] }],
    });
  }, [drawPrice, drawSub, s]);

  useEffect(() => {
    drawAll();
    let timer;
    const onResize = () => {
      clearTimeout(timer);
      timer = setTimeout(drawAll, 140);
    };
    window.addEventListener('resize', onResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', onResize);
    };
  }, [drawAll]);

  const onMove = (ev) => {
    const cv = priceRef.current;
    const geo = geomRef.current;
    if (!cv || !geo) return;
    const rect = cv.getBoundingClientRect();
    const clientX = ev.touches ? ev.touches[0].clientX : ev.clientX;
    const cx = clientX - rect.left;
    let i = Math.round(((cx - geo.PL) / geo.iw) * (n - 1));
    i = Math.max(0, Math.min(n - 1, i));
    setHover({ i, x: Math.min(rect.width - 150, Math.max(0, cx + 14)) });
  };

  return (
    <section className="chartbox">
      <div className="legend">
        <span>
          <i style={{ background: COLOURS.sma20 }} />
          20-day average
        </span>
        <span>
          <i style={{ background: COLOURS.sma50 }} />
          50-day
        </span>
        <span>
          <i style={{ background: COLOURS.sma200 }} />
          200-day
        </span>
        <span>
          <i style={{ background: COLOURS.up }} />
          target
        </span>
        <span>
          <i style={{ background: COLOURS.down }} />
          stop
        </span>
      </div>

      <canvas
        ref={priceRef}
        style={{ height: 340 }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        onTouchMove={onMove}
        onTouchEnd={() => setHover(null)}
      />

      <div className="panel-label">Relative strength (14)</div>
      <canvas ref={rsiRef} style={{ height: 96 }} />

      <div className="panel-label">MACD histogram (12, 26, 9)</div>
      <canvas ref={macdRef} style={{ height: 96 }} />

      {hover && (
        <div className="tip" style={{ left: hover.x, top: 24, opacity: 1 }}>
          {[
            new Date(s.t[hover.i]).toLocaleDateString(),
            `O ${fmt(s.o[hover.i])}   H ${fmt(s.h[hover.i])}`,
            `L ${fmt(s.l[hover.i])}   C ${fmt(s.c[hover.i])}`,
            s.rsi[hover.i] != null ? `RSI ${s.rsi[hover.i].toFixed(1)}` : '',
          ]
            .filter(Boolean)
            .join('\n')}
        </div>
      )}
    </section>
  );
}
