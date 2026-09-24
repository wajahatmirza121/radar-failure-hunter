/** Table of the worst scenarios for the selected detector. */
export default function FailureTable({ rows, threshold, shortTags }) {
  const fmt = (v, digits = 0) =>
    v <= -50 ? 'none' : Number(v).toFixed(digits)

  return (
    <div className="chart">
      <h3>Top failures</h3>
      <table>
        <thead>
          <tr>
            <th>Pd</th>
            <th>FA/map</th>
            <th>SNR dB</th>
            <th>CNR dB</th>
            <th>Int dB</th>
            <th>Δr</th>
            <th>Δd</th>
            <th>Doppler</th>
            <th>cluster</th>
            <th>mode</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={r.pd < threshold ? 'fail' : ''}>
              <td className="num">{r.pd.toFixed(2)}</td>
              <td className="num">{r.fa.toFixed(0)}</td>
              <td className="num">{r.snr_db.toFixed(1)}</td>
              <td className="num">{fmt(r.cnr_db)}</td>
              <td className="num">{fmt(r.int_db)}</td>
              <td className="num">{r.dr > 0 ? `+${r.dr}` : r.dr}</td>
              <td className="num">{r.dd > 0 ? `+${r.dd}` : r.dd}</td>
              <td className="num">{r.d}</td>
              <td className="num">{r.cluster >= 0 ? r.cluster : '—'}</td>
              <td>{shortTags[r.tag] ?? r.tag}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
