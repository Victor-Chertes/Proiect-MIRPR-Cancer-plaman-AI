import { LABELS } from '../labels.js'

export default function ResultCard({ result }) {
  const positive = result.prediction === 'POSITIVE'

  return (
    <div className={`result ${positive ? 'positive' : 'negative'}`}>
      <span className="result-label">Rezultat</span>
      <strong className="result-value">{LABELS[result.prediction]}</strong>
      <span className="result-text">
        {positive
          ? 'Au fost detectate semne de malignitate. Se recomandă evaluarea de către un specialist.'
          : 'Nu au fost detectate semne de malignitate.'}
      </span>
    </div>
  )
}
