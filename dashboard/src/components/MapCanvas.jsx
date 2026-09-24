import { useEffect, useRef } from 'react'

// heat colormap for normalized log-power: dark navy -> blue -> red -> amber -> pale yellow
const STOPS = [
  [0.0, [11, 18, 32]],
  [0.25, [30, 58, 138]],
  [0.55, [220, 38, 38]],
  [0.8, [251, 191, 36]],
  [1.0, [254, 243, 199]],
]

export function colormap(t) {
  const v = Math.max(0, Math.min(1, t))
  for (let i = 1; i < STOPS.length; i++) {
    if (v <= STOPS[i][0]) {
      const [t0, c0] = STOPS[i - 1]
      const [t1, c1] = STOPS[i]
      const f = (v - t0) / (t1 - t0)
      return c0.map((c, k) => Math.round(c + f * (c1[k] - c)))
    }
  }
  return STOPS[STOPS.length - 1][1]
}

function crosshair(ctx, cx, cy, s) {
  ctx.beginPath()
  ctx.moveTo(cx - s, cy)
  ctx.lineTo(cx + s, cy)
  ctx.moveTo(cx, cy - s)
  ctx.lineTo(cx, cy + s)
  ctx.stroke()
}

const MASK_COLORS = { 'CA-CFAR': 'rgba(96,165,250,0.45)', 'OS-CFAR': 'rgba(244,114,182,0.45)' }

/** Range-Doppler map: heat canvas + detection-mask overlays + target/interferer crosses. */
export default function MapCanvas({ map, detectors, active, target, interferer, interfererPresent }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!map || !ref.current) return
    const cv = ref.current
    const ctx = cv.getContext('2d')
    const H = map.length
    const W = map[0].length
    const img = ctx.createImageData(W, H)
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const [r, g, b] = colormap(map[y][x])
        const i = (y * W + x) * 4
        img.data[i] = r
        img.data[i + 1] = g
        img.data[i + 2] = b
        img.data[i + 3] = 255
      }
    }
    const off = document.createElement('canvas')
    off.width = W
    off.height = H
    off.getContext('2d').putImageData(img, 0, 0)
    ctx.imageSmoothingEnabled = false
    ctx.clearRect(0, 0, cv.width, cv.height)
    ctx.drawImage(off, 0, 0, cv.width, cv.height)

    const sx = cv.width / W
    const sy = cv.height / H
    for (const det of detectors ?? []) {
      if (!active?.includes(det.name)) continue
      ctx.fillStyle = MASK_COLORS[det.name] ?? 'rgba(255,255,255,0.4)'
      for (let y = 0; y < H; y++)
        for (let x = 0; x < W; x++)
          if (det.mask[y][x]) ctx.fillRect(x * sx, y * sy, Math.ceil(sx), Math.ceil(sy))
    }

    ctx.lineWidth = 2
    ctx.strokeStyle = '#34d399'                                   // target: green cross
    crosshair(ctx, target[1] * sx + sx / 2, target[0] * sy + sy / 2, 7)
    if (interfererPresent) {                                      // interferer: orange cross
      ctx.strokeStyle = '#fb923c'
      crosshair(ctx, interferer[1] * sx + sx / 2, interferer[0] * sy + sy / 2, 7)
    }
  }, [map, detectors, active, target, interferer, interfererPresent])

  return <canvas ref={ref} width={640} height={320} className="mapCanvas" />
}
