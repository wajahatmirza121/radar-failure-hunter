// Small SVG chart components — no chart library, so the dashboard stays dependency-light.

export function colorForPd(pd, thr) {
  // interpolate amber (pd = thr, marginal) -> deep red (pd = 0, total failure)
  const t = Math.max(0, Math.min(1, pd / thr))
  const from = [185, 28, 28] // #b91c1c
  const to = [251, 191, 36] // #fbbf24
  const c = from.map((f, i) => Math.round(f + t * (to[i] - f)))
  return `rgb(${c[0]},${c[1]},${c[2]})`
}

export function ticks(min, max, step) {
  const out = []
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(v)
  return out
}

export const DETECTOR_COLORS = { 'CA-CFAR': '#60a5fa', 'OS-CFAR': '#f472b6' }
const PALETTE = ['#34d399', '#fbbf24', '#a78bfa', '#f87171', '#22d3ee']

export function detectorColor(name, idx = 0) {
  return DETECTOR_COLORS[name] ?? PALETTE[idx % PALETTE.length]
}

export const SHORT_TAGS = {
  'target masking by interferer in training cells': 'interferer masking',
  'clutter-ridge leakage into training cells': 'clutter-ridge leakage',
  'low SNR / other': 'low SNR / other',
}
