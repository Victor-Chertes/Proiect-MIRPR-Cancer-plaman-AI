import { LABELS } from '../labels.js'

export default function History({ items }) {
  return (
    <section className="history">
      <h2>Analize anterioare</h2>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <img src={item.thumb} alt="" />
            <span className="history-name" title={item.filename}>{item.filename}</span>
            <span className="history-time">
              {new Date(item.timestamp).toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span className={`tag ${item.prediction === 'POSITIVE' ? 'positive' : 'negative'}`}>
              {LABELS[item.prediction]}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
