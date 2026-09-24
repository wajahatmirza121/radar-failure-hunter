import { ticks } from './chartUtils.js'

/** Horizontal bar chart: items = [{label, value, color, faint}] */
export default function BarChart({ title, unit, items }) {
  const W = 460
  const rowH = 34
  const labelW = 170
  const H = 30 + items.length * rowH + 8
  const max = Math.max(1, ...items.map((it) => it.value)) * 1.15
  const scale = (v) => (v / max) * (W - labelW - 48)

  return (
    <div className="chart">
      <h3>{title}</h3>
      <svg width={W} height={H} role="img" aria-label={title}>
        {ticks(0, max, max / 4).map((v) => (
          <g key={v}>
            <line
              x1={labelW + scale(v)}
              x2={labelW + scale(v)}
              y1={24}
              y2={H - 6}
              stroke="#243244"
              strokeDasharray="2 4"
            />
            <text x={labelW + scale(v)} y={16} fill="#7d8ca3" fontSize={10} textAnchor="middle">
              {v.toFixed(0)}
            </text>
          </g>
        ))}
        {items.map((it, i) => {
          const y = 30 + i * rowH
          const w = Math.max(1, scale(it.value))
          return (
            <g key={it.label}>
              <text x={labelW - 8} y={y + 14} fill="#c7d2e0" fontSize={11} textAnchor="end">
                {it.label}
              </text>
              <rect
                x={labelW}
                y={y}
                width={w}
                height={20}
                rx={3}
                fill={it.color}
                opacity={it.faint ? 0.45 : 0.95}
              />
              <text
                x={labelW + w + 6}
                y={y + 14}
                fill="#e6edf6"
                fontSize={11}
                fontWeight={600}
              >
                {it.value.toFixed(it.value >= 10 ? 0 : 1)}
                {unit === '%' ? '%' : ''}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
