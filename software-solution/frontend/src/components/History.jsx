export default function History({ items }) {
  return (
    <section className="history">
      <h2>Recent analyses</h2>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <img src={item.thumb} alt="" />
            <div className="history-info">
              <span className="history-name" title={item.filename}>{item.filename}</span>
              <span className="history-time">
                {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <span className={`tag ${item.prediction === 'POSITIVE' ? 'positive' : 'negative'}`}>
              {item.prediction}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
