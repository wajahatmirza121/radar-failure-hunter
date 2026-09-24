import { useCallback, useEffect, useState } from 'react'
import BarChart from './components/BarChart.jsx'
import Clusters from './components/Clusters.jsx'
import FailureTable from './components/FailureTable.jsx'
import HuntCard from './components/HuntCard.jsx'
import Lab from './components/Lab.jsx'
import ScatterPlot from './components/ScatterPlot.jsx'
import ValidationCurve from './components/ValidationCurve.jsx'
import { SHORT_TAGS, detectorColor } from './components/chartUtils.js'

export default function App() {
  const [view, setView] = useState('lab')
  const [atlas, setAtlas] = useState(null)
  const [error, setError] = useState(null)
  const [detIdx, setDetIdx] = useState(0)

  const loadAtlas = useCallback(async () => {
    for (const url of ['/api/atlas', './atlas.json']) {
      try {
        const r = await fetch(url)
        if (r.ok) {
          setAtlas(await r.json())
          setError(null)
          return
        }
      } catch {
        /* try the next source */
      }
    }
    setError('Could not load atlas.json — run `python hunter.py hunt` first.')
  }, [])

  useEffect(() => {
    loadAtlas()
  }, [loadAtlas])

  return (
    <div className="app">
      <header>
        <h1>radar-failure-hunter</h1>
        <div className="nav">
          <button className={view === 'lab' ? 'active' : ''} onClick={() => setView('lab')}>
            Scenario Lab
          </button>
          <button className={view === 'report' ? 'active' : ''} onClick={() => setView('report')}>
            Hunt Report
          </button>
        </div>
      </header>

      {view === 'lab' ? (
        <Lab />
      ) : (
        <ReportView
          atlas={atlas}
          error={error}
          detIdx={detIdx}
          setDetIdx={setDetIdx}
          onHuntFinished={loadAtlas}
        />
      )}

      <footer>
        regenerate the hunt with <code>python hunter.py hunt</code> · web app with{' '}
        <code>python hunter.py serve</code> · tests with <code>python -m pytest</code>
      </footer>
    </div>
  )
}

function ReportView({ atlas, error, detIdx, setDetIdx, onHuntFinished }) {
  if (error) {
    return (
      <div className="error">
        {error}. The Scenario Lab tab works without an atlas; or re-run the hunt below.
        <HuntCard onFinished={onHuntFinished} />
      </div>
    )
  }
  if (!atlas) return <div className="loading">Loading atlas.json…</div>

  const { meta, detectors } = atlas
  const det = detectors[Math.min(detIdx, detectors.length - 1)]
  const thr = meta.failure_pd_threshold ?? 0.3
  const failures = (det.top_failures ?? []).filter((r) => r.pd < thr)

  const yieldBars = detectors.flatMap((d, i) => [
    { label: `${d.name} · adaptive`, value: d.yield_adaptive, color: detectorColor(d.name, i) },
    { label: `${d.name} · random`, value: d.yield_random, color: detectorColor(d.name, i), faint: true },
  ])
  const faBars = detectors.map((d, i) => ({
    label: d.name,
    value: d.fa_map_in_clutter,
    color: detectorColor(d.name, i),
  }))

  const exportCsv = () => {
    const cols = ['pd', 'fa', 'snr_db', 'r', 'd', 'cnr_db', 'int_db', 'dr', 'dd', 'tag', 'cluster']
    const lines = [['detector', ...cols].join(',')]
    for (const d of detectors) {
      for (const row of d.top_failures ?? []) {
        lines.push([d.name, ...cols.map((c) => row[c] ?? '')].join(','))
      }
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'radar-failure-hunter-top-failures.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <>
      <p className="meta">
        map {meta.map[0]}×{meta.map[1]} · guard {meta.guard_cells} · training ring{' '}
        {meta.training_ring} cells · Pfa {meta.pfa.toExponential(0)} ·{' '}
        {meta.trials_per_scenario} trials/scenario · failure = Pd &lt; {thr}
      </p>
      <p className="meta">
        worst Pd: {detectors.map((d) => `${d.name} ${d.worst_pd.toFixed(2)}`).join('  ·  ')} ·
        generated {meta.generated}
      </p>

      <HuntCard onFinished={onHuntFinished} />

      <ValidationCurve detectors={detectors} pfa={meta.pfa} />

      <section className="charts">
        <BarChart
          title={`Failure yield (Pd < ${thr}), % of evaluated scenarios`}
          unit="%"
          items={yieldBars}
        />
        <BarChart
          title="False alarms per map in clutter scenarios (same draws for all detectors)"
          unit="FA/map"
          items={faBars}
        />
      </section>

      <div className="tabs">
        {detectors.map((d, i) => (
          <button key={d.name} className={i === detIdx ? 'active' : ''} onClick={() => setDetIdx(i)}>
            {d.name}
          </button>
        ))}
      </div>

      <ScatterPlot rows={failures} threshold={thr} />

      <Clusters detector={det} />

      <FailureTable
        rows={(det.top_failures ?? []).slice(0, 12)}
        threshold={thr}
        shortTags={SHORT_TAGS}
      />

      <div className="formRow">
        <button onClick={exportCsv}>
          Export top {detectors.reduce((n, d) => n + (d.top_failures?.length ?? 0), 0)} failures as CSV
        </button>
      </div>
    </>
  )
}
