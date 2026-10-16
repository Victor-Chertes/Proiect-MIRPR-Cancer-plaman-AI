export default function ResultCard({ result }) {
  const positive = result.prediction === 'POSITIVE'
  const pct = Math.round(result.confidence * 100)

  return (
    <div className={`result ${positive ? 'positive' : 'negative'}`}>
      <span className="result-label">Prediction</span>
      <span className="result-value">{result.prediction}</span>
      <p className="result-text">
        {positive
          ? 'Findings consistent with a malignant nodule. Refer for specialist review.'
          : 'No signs of malignancy detected in this scan.'}
      </p>

      <div className="meter">
        <div className="meter-head">
          <span>Confidence</span>
          <span className="meter-value">{pct}%</span>
        </div>
        <div className="meter-track">
          <div className="meter-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <dl className="result-meta">
        <div>
          <dt>Model</dt>
          <dd>{result.model}</dd>
        </div>
        <div>
          <dt>Time</dt>
          <dd>{result.inference_ms} ms</dd>
        </div>
      </dl>
    </div>
  )
}
