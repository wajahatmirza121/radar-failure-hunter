import { useCallback, useEffect, useState } from 'react'
import MapCanvas from './MapCanvas.jsx'
import SweepChart from './SweepChart.jsx'
import { detectorColor } from './chartUtils.js'

const DEFAULTS = {
  snr_db: 15,
  cnrOn: true,
  cnr_db: 20,
  intOn: true,
  int_db: 25,
  dr: 6,
  dd: 3,
  r: 64,
  d: 32,
  seed: 42,
  trials: 60,
}

// One-click scenarios reproducing the failure modes found by the hunt
const PRESETS = [
  { name: 'Clean', params: { snr_db: 16, cnrOn: false, intOn: false, d: 32 } },
  { name: 'Interferer masking', params: { snr_db: 15, cnrOn: false, intOn: true, int_db: 25, dr: 6, dd: 3 } },
  { name: 'Clutter edge', params: { snr_db: 15, cnrOn: true, cnr_db: 22, intOn: false, d: 8 } },
  { name: 'Low SNR', params: { snr_db: 8, cnrOn: false, intOn: false } },
  { name: 'Adversarial worst', params: { snr_db: 14.7, cnrOn: true, cnr_db: 20, intOn: true, int_db: 13, dr: -7, dd: -1, d: 7 } },
]

const scenarioBody = (p) => ({
  snr_db: p.snr_db,
  cnr_db: p.cnrOn ? p.cnr_db : -60,
  int_db: p.intOn ? p.int_db : -60,
  dr: p.dr,
  dd: p.dd,
  r: p.r,
  d: p.d,
  seed: p.seed,
})

/** Scenario Lab: user inputs radar parameters, gets live map + detection + Monte-Carlo output. */
export default function Lab() {
  const [p, setP] = useState(DEFAULTS)
  const [sim, setSim] = useState(null)
  const [mc, setMc] = useState(null)
  const [sweep, setSweep] = useState(null)
  const [busySim, setBusySim] = useState(false)
  const [busyMc, setBusyMc] = useState(false)
  const [busySweep, setBusySweep] = useState(false)
  const [active, setActive] = useState(['CA-CFAR'])
  const [error, setError] = useState(null)

  const set = (k) => (v) => setP((old) => ({ ...old, [k]: v }))

  const runSim = useCallback(async (params) => {
    setBusySim(true)
    setError(null)
    try {
      const r = await fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenarioBody(params)),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setSim(await r.json())
      try {                                          // shareable URL: ?s=<scenario>
        const q = new URLSearchParams({ s: JSON.stringify(scenarioBody(params)) })
        window.history.replaceState(null, '', `${window.location.pathname}?${q}`)
      } catch { /* URL sync is best-effort */ }
    } catch (e) {
      setError(`Simulate failed (${e}). Is the server running? python hunter.py serve`)
    } finally {
      setBusySim(false)
    }
  }, [])

  const runMc = useCallback(async () => {
    setBusyMc(true)
    setError(null)
    try {
      const r = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...scenarioBody(p), trials: p.trials }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setMc(await r.json())
    } catch (e) {
      setError(`Monte-Carlo failed (${e}).`)
    } finally {
      setBusyMc(false)
    }
  }, [p])

  const runSweep = useCallback(async () => {
    setBusySweep(true)
    setError(null)
    try {
      const r = await fetch('/api/sweep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...scenarioBody(p), snr_lo: 4, snr_hi: 32, snr_step: 4,
                                trials: Math.min(p.trials, 50) }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setSweep(await r.json())
    } catch (e) {
      setError(`Sweep failed (${e}).`)
    } finally {
      setBusySweep(false)
    }
  }, [p])

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('s')   // restore shared scenario
    let initial = DEFAULTS
    if (q) {
      try {
        const shared = JSON.parse(q)
        initial = { ...DEFAULTS, ...shared,
                    cnrOn: shared.cnr_db > -50, intOn: shared.int_db > -50 }
      } catch { /* ignore malformed links */ }
    }
    setP(initial)
    runSim(initial)                                  // show output immediately on open
  }, [runSim])

  const applyPreset = (preset) => {
    const next = { ...p, ...preset.params }
    setP(next)
    setSweep(null)
    setMc(null)
    runSim(next)
  }

  return (
    <div className="lab">
      <section className="chart form">
        <h3>Scenario input</h3>
        <div className="presetRow">
          {PRESETS.map((pr) => (
            <button key={pr.name} className="preset" onClick={() => applyPreset(pr)}>
              {pr.name}
            </button>
          ))}
        </div>
        <Slider label="target SNR" unit="dB" min={0} max={40} step={0.5} value={p.snr_db} onChange={set('snr_db')} />
        <Slider label="Doppler bin d" min={0} max={63} step={1} value={p.d} onChange={set('d')} />
        <Slider label="range bin r" min={8} max={119} step={1} value={p.r} onChange={set('r')} />
        <Check label="clutter ridge" checked={p.cnrOn} onChange={set('cnrOn')} />
        {p.cnrOn && (
          <Slider label="clutter CNR" unit="dB" min={0} max={30} step={0.5} value={p.cnr_db} onChange={set('cnr_db')} />
        )}
        <Check label="interferer" checked={p.intOn} onChange={set('intOn')} />
        {p.intOn && (
          <>
            <Slider label="interferer power" unit="dB" min={0} max={30} step={0.5} value={p.int_db} onChange={set('int_db')} />
            <Slider label="interferer Δr" unit="bins" min={-10} max={10} step={1} value={p.dr} onChange={set('dr')} />
            <Slider label="interferer Δd" unit="bins" min={-5} max={5} step={1} value={p.dd} onChange={set('dd')} />
          </>
        )}
        <Slider label="seed" min={0} max={999} step={1} value={p.seed} onChange={set('seed')} />
        <div className="formRow">
          <button className="primary" disabled={busySim} onClick={() => runSim(p)}>
            {busySim ? 'Simulating…' : 'Generate map'}
          </button>
          <button disabled={busyMc} onClick={runMc}>
            {busyMc ? `Running ${p.trials} trials…` : 'Run Monte-Carlo'}
          </button>
        </div>
        <div className="formRow">
          <button disabled={busySweep} onClick={runSweep}>
            {busySweep ? 'Sweeping…' : 'Sweep SNR 4→32 dB'}
          </button>
          <label>
            trials
            <input
              type="number"
              min={10}
              max={400}
              value={p.trials}
              onChange={(e) => set('trials')(Number(e.target.value))}
            />
          </label>
        </div>
        {error && <div className="error">{error}</div>}
      </section>

      <section className="chart results">
        <h3>Output — range-Doppler map (log power)</h3>
        {sim && (
          <>
            <MapCanvas
              map={sim.map}
              detectors={sim.detectors}
              active={active}
              target={sim.target}
              interferer={sim.interferer}
              interfererPresent={sim.interferer_present}
            />
            <div className="legendRow">
              <span className="swatch" style={{ background: '#34d399' }} /> target
              {sim.interferer_present && (
                <>
                  <span className="swatch" style={{ background: '#fb923c' }} /> interferer
                </>
              )}
              {sim.detectors.map((d) => (
                <label key={d.name} className="checkInline">
                  <input
                    type="checkbox"
                    checked={active.includes(d.name)}
                    onChange={(e) =>
                      setActive((old) =>
                        e.target.checked ? [...old, d.name] : old.filter((n) => n !== d.name),
                      )
                    }
                  />
                  <span className="swatch" style={{ background: detectorColor(d.name), opacity: 0.6 }} />
                  {d.name} detections
                </label>
              ))}
              <span className="hint">x: Doppler bin · y: range bin</span>
            </div>
            <div className="statRow">
              {sim.detectors.map((d) => (
                <div className="stat" key={d.name}>
                  <div className="statName" style={{ color: detectorColor(d.name) }}>{d.name}</div>
                  <div>
                    target hit: <strong>{d.hit ? 'YES' : 'no'}</strong>
                  </div>
                  <div>
                    false alarms: <strong>{d.false_alarms}</strong> · detections: {d.detections}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {mc && (
          <>
            <h3>
              Monte-Carlo output — {mc.trials} trials, seed {mc.seed} (identical noise for both
              detectors)
            </h3>
            <div className="statRow">
              {mc.results.map((r, i) => (
                <div className="stat" key={r.name}>
                  <div className="statName" style={{ color: detectorColor(r.name, i) }}>{r.name}</div>
                  <div>
                    Pd: <strong>{(r.pd * 100).toFixed(1)}%</strong>
                  </div>
                  <div className="pdBar">
                    <div
                      className="pdFill"
                      style={{ width: `${Math.round(r.pd * 100)}%`, background: detectorColor(r.name, i) }}
                    />
                  </div>
                  <div>
                    false alarms/map: <strong>{r.fa.toFixed(2)}</strong>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {sweep && <SweepChart sweep={sweep} />}

        <p className="hint">
          Try: an interferer within ~10 range / ~5 Doppler bins of the target masks CA-CFAR but not
          OS-CFAR; near the clutter ridge (Doppler 0-10), OS-CFAR floods false alarms. The URL
          always contains your scenario — copy it to share this exact view.
        </p>
      </section>
    </div>
  )
}

function Slider({ label, unit, min, max, step, value, onChange }) {
  return (
    <label className="field">
      <span className="fieldLabel">
        {label} <strong>{value}{unit ? ` ${unit}` : ''}</strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  )
}

function Check({ label, checked, onChange }) {
  return (
    <label className="field checkInline">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  )
}
