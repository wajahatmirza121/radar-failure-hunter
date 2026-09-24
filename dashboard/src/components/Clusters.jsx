import { SHORT_TAGS, detectorColor } from './chartUtils.js'

const fmtDb = (v) => (v <= -50 ? 'none' : `${v.toFixed(0)} dB`)

/** Failure clusters of the selected detector, with rule-based explanations. */
export default function Clusters({ detector }) {
  const clusters = detector.clusters ?? []
  const color = detectorColor(detector.name)
  return (
    <div className="chart">
      <h3>Failure clusters (KMeans over scenarios below the failure threshold) — why it fails</h3>
      {clusters.length === 0 ? (
        <p className="empty">
          {detector.name} had no scenarios with Pd below the failure threshold — nothing to cluster.
        </p>
      ) : (
        <div className="clusterList">
          {clusters.map((c) => (
            <div className="cluster" key={c.id} style={{ borderLeftColor: color }}>
              <div className="clusterHead">
                <strong>Cluster {c.id}</strong>
                <span className="pill">{c.size} scenarios</span>
                <span className="pill">mean Pd {c.mean_pd.toFixed(2)}</span>
                <span className="pill tag">{SHORT_TAGS[c.tag] ?? c.tag}</span>
              </div>
              <div className="centroid">
                target SNR {c.centroid.snr_db.toFixed(1)} dB · clutter {fmtDb(c.centroid.cnr_db)} ·
                interferer {fmtDb(c.centroid.int_db)} · Δ({c.centroid.dr.toFixed(1)},{' '}
                {c.centroid.dd.toFixed(1)}) bins · Doppler bin {c.centroid.d.toFixed(0)}
              </div>
              {c.explanation && (
                <p className="explanation">{c.explanation.replace(/\*\*/g, '')}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
