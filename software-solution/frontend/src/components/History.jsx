import { LABELS, formatTime } from '../format.js'

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
                <th>Fișier</th>
                <th>Rezultat</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="mono">{formatTime(item.timestamp)}</td>
                  <td className="file-cell">
                    <div>
                      <img src={item.thumb} alt="" />
                      <span title={item.filename}>{item.filename}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`chip ${item.prediction.toLowerCase()}`}>{LABELS[item.prediction]}</span>
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
