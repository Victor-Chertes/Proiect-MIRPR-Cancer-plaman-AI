import { formatTime } from '../format.js'

export default function History({ items }) {
  return (
    <section className="history" aria-label="Istoric">
      <h2>Istoric sesiune</h2>
      {items.length === 0 ? (
        <p className="history-empty">Analizele efectuate în această sesiune vor apărea aici.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Ora</th>
                <th>Pacient</th>
                <th>Fișier</th>
                <th>Biomarkeri pozitivi</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="mono">{formatTime(item.timestamp)}</td>
                  <td className="mono">
                    {[item.patientId, `${item.patient.age} ani`, item.patient.sex].filter(Boolean).join(' · ')}
                  </td>
                  <td className="file-cell">
                    <div>
                      {item.thumb ? <img src={item.thumb} alt="" /> : <span className="thumb-3d">CT</span>}
                      <span title={item.filename}>{item.filename}</span>
                    </div>
                  </td>
                  <td className="chips">
                    {item.biomarkers.some((b) => b.positive)
                      ? item.biomarkers.filter((b) => b.positive).map((b) => (
                          <span key={b.name} className="chip positive">{b.name}</span>
                        ))
                      : <span className="chip negative">Niciunul</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
