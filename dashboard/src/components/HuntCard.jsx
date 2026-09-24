import { useEffect, useRef, useState } from 'react'

/** Run the failure search from the browser: quick (~1 min) or full (~4 min) budget. */
export default function HuntCard({ onFinished }) {
  const [st, setSt] = useState({ running: false, lines: [], done: false, error: null })
  const wasRunning = useRef(false)
  const notified = useRef(false)

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const r = await fetch('/api/hunt/status')
        const s = await r.json()
        if (cancelled) return
        setSt(s)
        if (wasRunning.current && !s.running && s.done && !notified.current) {
          notified.current = true
          onFinished()                               // atlas.json changed -> reload report
        }
        wasRunning.current = s.running
      } catch {
        /* backend unreachable - keep last state */
      }
    }
    poll()
    const id = setInterval(poll, 2000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [onFinished])

  const start = async (quick) => {
    notified.current = false
    setSt({ running: true, lines: [], done: false, error: null })
    try {
      await fetch('/api/hunt/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quick }),
      })
    } catch (e) {
      setSt({ running: false, lines: [], done: false, error: String(e) })
    }
  }

  return (
    <div className="chart huntCard">
      <h3>Re-run the failure search (deterministic seeds — same numbers every time)</h3>
      <div className="formRow">
        <button disabled={st.running} onClick={() => start(true)}>
          Quick hunt (~1 min)
        </button>
        <button disabled={st.running} onClick={() => start(false)}>
          Full hunt (~4 min)
        </button>
        {st.running && <span className="hint">running…</span>}
      </div>
      {st.running && st.lines?.length > 0 && (
        <pre className="progress">{st.lines.slice(-6).join('\n')}</pre>
      )}
      {st.done && !st.running && (
        <p className="hint">
          Hunt finished at {st.finished} — atlas.json and report.md were rewritten; the report
          below has been refreshed.
        </p>
      )}
      {st.error && <div className="error">{st.error}</div>}
    </div>
  )
}
