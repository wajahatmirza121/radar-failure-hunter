import { detectorColor, ticks } from './chartUtils.js'

const M = { t: 18, r: 16, b: 36, l: 44 }
const W = 760
const H = 300

/** Clean-scenario Pd vs SNR for every detector, against Swerling-I theory. */
export default function ValidationCurve({ detectors, pfa }) {
  const curve = detectors[0].curve
  const X0 = curve[0].snr_db
  const X1 = curve[curve.length - 1].snr_db
  const x = (v) => M.l + ((v - X0) / (X1 - X0)) * (W - M.l - M.r)
  const y = (v) => H - M.b - v * (H - M.t - M.b)
  const theory = (snr) => Math.pow(pfa, 1 / (1 + Math.pow(10, snr / 10)))
  const snrs = curve.map((r) => r.snr_db)
  const path = (pts) =>
    pts.map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')
  const legendX = (i) => M.l + 10 + i * 140

  return (
    <div className="chart">
      <h3>
        Validation — clean-scenario Pd vs SNR (dashed: Swerling-I theory Pd = Pfa^(1/(1+SNR)))
      </h3>
      <svg width={W} height={H} role="img" aria-label="Validation curve, Pd versus SNR">
        {ticks(0, 1, 0.2).map((v) => (
          <g key={`y${v}`}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} stroke="#1d2a3a" />
            <text x={M.l - 8} y={y(v) + 4} fill="#7d8ca3" fontSize={11} textAnchor="end">
              {v.toFixed(1)}
            </text>
          </g>
        ))}
        {snrs.map((v) => (
          <g key={`x${v}`}>
            <line x1={x(v)} x2={x(v)} y1={M.t} y2={H - M.b} stroke="#1d2a3a" />
            <text x={x(v)} y={H - M.b + 16} fill="#7d8ca3" fontSize={11} textAnchor="middle">
              {v}
            </text>
          </g>
        ))}
        <path d={path(snrs.map((s) => [s, theory(s)]))} fill="none" stroke="#9fb0c6" strokeDasharray="5 4" />
        {detectors.map((d, i) => (
          <g key={d.name}>
            <path
              d={path(d.curve.map((r) => [r.snr_db, r.pd]))}
              fill="none"
              stroke={detectorColor(d.name, i)}
              strokeWidth={2}
            />
            {d.curve.map((r) => (
              <circle key={r.snr_db} cx={x(r.snr_db)} cy={y(r.pd)} r={3} fill={detectorColor(d.name, i)}>
                <title>{`${d.name}: Pd ${r.pd.toFixed(2)}, ${r.fa.toFixed(2)} FA/map @ ${r.snr_db} dB`}</title>
              </circle>
            ))}
            <line
              x1={legendX(i)}
              y1={M.t + 2}
              x2={legendX(i) + 20}
              y2={M.t + 2}
              stroke={detectorColor(d.name, i)}
              strokeWidth={2}
            />
            <text x={legendX(i) + 25} y={M.t + 6} fill="#c7d2e0" fontSize={11}>
              {d.name}
            </text>
          </g>
        ))}
        <line
          x1={legendX(detectors.length)}
          y1={M.t + 2}
          x2={legendX(detectors.length) + 20}
          y2={M.t + 2}
          stroke="#9fb0c6"
          strokeDasharray="5 4"
        />
        <text x={legendX(detectors.length) + 25} y={M.t + 6} fill="#c7d2e0" fontSize={11}>
          theory
        </text>
        <text x={(W + M.l) / 2} y={H - 6} fill="#9fb0c6" fontSize={12} textAnchor="middle">
          SNR (dB)
        </text>
      </svg>
    </div>
  )
}
