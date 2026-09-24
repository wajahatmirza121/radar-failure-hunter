import { detectorColor, ticks } from './chartUtils.js'

const M = { t: 18, r: 16, b: 34, l: 44 }
const W = 640
const H = 260

/** Pd vs SNR sweep for the user's scenario, one line per detector. */
export default function SweepChart({ sweep }) {
  const pts = sweep.series.flatMap((s) => s.points)
  if (!pts.length) return null
  const X0 = Math.min(...pts.map((p) => p.snr_db))
  const X1 = Math.max(...pts.map((p) => p.snr_db))
  const x = (v) => M.l + ((v - X0) / (X1 - X0 || 1)) * (W - M.l - M.r)
  const y = (v) => H - M.b - v * (H - M.t - M.b)
  const path = (points) =>
    points.map((p, i) => `${i ? 'L' : 'M'}${x(p.snr_db).toFixed(1)},${y(p.pd).toFixed(1)}`).join(' ')

  return (
    <div className="chart">
      <h3>
        SNR sweep for your scenario — {sweep.trials} trials/point, seed {sweep.seed} (hover points
        for FA/map)
      </h3>
      <svg width={W} height={H} role="img" aria-label="Pd versus SNR sweep">
        {ticks(0, 1, 0.2).map((v) => (
          <g key={`y${v}`}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} stroke="#1d2a3a" />
            <text x={M.l - 8} y={y(v) + 4} fill="#7d8ca3" fontSize={11} textAnchor="end">
              {v.toFixed(1)}
            </text>
          </g>
        ))}
        {ticks(X0, X1, 4).map((v) => (
          <g key={`x${v}`}>
            <line x1={x(v)} x2={x(v)} y1={M.t} y2={H - M.b} stroke="#1d2a3a" />
            <text x={x(v)} y={H - M.b + 16} fill="#7d8ca3" fontSize={11} textAnchor="middle">
              {v}
            </text>
          </g>
        ))}
        {sweep.series.map((s, i) => {
          const color = detectorColor(s.name, i)
          return (
            <g key={s.name}>
              <path d={path(s.points)} fill="none" stroke={color} strokeWidth={2} />
              {s.points.map((p) => (
                <circle key={p.snr_db} cx={x(p.snr_db)} cy={y(p.pd)} r={3.5} fill={color}>
                  <title>
                    {`${s.name}: Pd ${p.pd.toFixed(2)}, ${p.fa.toFixed(2)} FA/map @ ${p.snr_db} dB`}
                  </title>
                </circle>
              ))}
              <text x={M.l + 10 + i * 110} y={M.t + 6} fill={color} fontSize={11} fontWeight={600}>
                {s.name}
              </text>
            </g>
          )
        })}
        <text x={(W + M.l) / 2} y={H - 4} fill="#9fb0c6" fontSize={12} textAnchor="middle">
          target SNR (dB)
        </text>
      </svg>
    </div>
  )
}
