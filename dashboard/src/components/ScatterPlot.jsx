import { colorForPd, ticks } from './chartUtils.js'

const M = { t: 14, r: 14, b: 36, l: 56 }
const W = 760
const H = 400
const X0 = 12.5 // target SNR range in dB
const X1 = 25.5
const Y0 = -70 // interferer power range in dB (-60 encodes "no interferer")
const Y1 = 34

/** Scatter of failing scenarios: x = target SNR, y = interferer power, color = Pd. */
export default function ScatterPlot({ rows, threshold }) {
  const x = (v) => M.l + ((v - X0) / (X1 - X0)) * (W - M.l - M.r)
  const y = (v) => H - M.b - ((v - Y0) / (Y1 - Y0)) * (H - M.t - M.b)

  return (
    <div className="chart">
      <h3>
        Failing scenarios — target SNR vs interferer power (color: Pd, darker = worse; hollow
        markers = no interferer)
      </h3>
      <svg width={W} height={H} role="img" aria-label="Scatter of failing scenarios">
        {ticks(X0, X1, 2).map((v) => (
          <g key={`x${v}`}>
            <line x1={x(v)} x2={x(v)} y1={M.t} y2={H - M.b} stroke="#1d2a3a" />
            <text x={x(v)} y={H - M.b + 16} fill="#7d8ca3" fontSize={11} textAnchor="middle">
              {v.toFixed(0)}
            </text>
          </g>
        ))}
        {ticks(Y0, Y1, 10).map((v) => (
          <g key={`y${v}`}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} stroke="#1d2a3a" />
            <text x={M.l - 8} y={y(v) + 4} fill="#7d8ca3" fontSize={11} textAnchor="end">
              {v.toFixed(0)}
            </text>
          </g>
        ))}
        <text x={(W + M.l) / 2} y={H - 6} fill="#9fb0c6" fontSize={12} textAnchor="middle">
          target SNR (dB)
        </text>
        <text
          x={14}
          y={(H - M.b + M.t) / 2}
          fill="#9fb0c6"
          fontSize={12}
          textAnchor="middle"
          transform={`rotate(-90 14 ${(H - M.b + M.t) / 2})`}
        >
          interferer power (dB, -60 = none)
        </text>

        {rows.map((r, i) => {
          const none = r.int_db <= -50
          return (
            <circle
              key={i}
              cx={x(r.snr_db)}
              cy={y(r.int_db)}
              r={4}
              fill={none ? 'none' : colorForPd(r.pd, threshold)}
              stroke={colorForPd(r.pd, threshold)}
              strokeWidth={none ? 1.5 : 1}
              fillOpacity={none ? 0 : 0.85}
            >
              <title>
                {`Pd ${r.pd.toFixed(2)} · SNR ${r.snr_db.toFixed(1)} dB · CNR ${r.cnr_db.toFixed(0)} dB · Int ${r.int_db.toFixed(0)} dB · Δ(${r.dr},${r.dd}) · FA/map ${r.fa.toFixed(0)}`}
              </title>
            </circle>
          )
        })}
      </svg>
    </div>
  )
}
