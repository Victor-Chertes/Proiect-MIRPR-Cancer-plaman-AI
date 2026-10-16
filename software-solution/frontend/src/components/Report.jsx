import { useRef } from 'react'
import { ACCEPTED, LABELS, formatSize, validate } from '../format.js'

const CONCLUSION = {
  POSITIVE: 'Aspect sugestiv pentru un nodul pulmonar malign. Se recomandă evaluare suplimentară de către un specialist.',
  NEGATIVE: 'Nu au fost identificate leziuni cu aspect malign pe imaginea analizată.',
}

export default function Report({ scan, status, result, error, onAnalyze, onReplace }) {
  const input = useRef(null)
  const busy = status === 'loading'

  return (
    <section className="report" aria-label="Raport">
      <h2 className="report-head">Raport</h2>

      <dl className="fields">
        <div>
          <dt>Investigație</dt>
          <dd>CT toracic, felie axială</dd>
        </div>
        <div>
          <dt>Fișier</dt>
          <dd className="mono" title={scan?.file.name}>{scan ? scan.file.name : '—'}</dd>
        </div>
        <div>
          <dt>Rezoluție</dt>
          <dd className="mono">{scan?.width ? `${scan.width} × ${scan.height} px` : '—'}</dd>
        </div>
        <div>
          <dt>Dimensiune</dt>
          <dd className="mono">{scan ? formatSize(scan.file.size) : '—'}</dd>
        </div>
      </dl>

      <div className={`conclusion ${result ? result.prediction.toLowerCase() : ''}`}>
        <h3>Concluzie</h3>
        {status === 'done' && result ? (
          <>
            <p className="verdict">{LABELS[result.prediction]}</p>
            <p className="verdict-text">{CONCLUSION[result.prediction]}</p>
          </>
        ) : status === 'error' ? (
          <p className="error" role="alert">{error}</p>
        ) : busy ? (
          <p className="pending">Se analizează imaginea…</p>
        ) : (
          <p className="pending">{scan ? 'Imaginea este pregătită pentru analiză.' : 'Încărcați o imagine pentru a începe.'}</p>
        )}
      </div>

      <div className="report-actions">
        {status === 'done' ? (
          <button className="btn primary" onClick={() => input.current?.click()}>
            Analizează altă imagine
          </button>
        ) : (
          <>
            <button className="btn primary" onClick={onAnalyze} disabled={!scan || busy}>
              {busy ? 'Se analizează…' : 'Analizează imaginea'}
            </button>
            {scan && (
              <button className="btn" onClick={() => input.current?.click()} disabled={busy}>
                Altă imagine
              </button>
            )}
          </>
        )}
        <input
          ref={input}
          id="replace-file"
          type="file"
          accept={ACCEPTED.join(',')}
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0]
            e.target.value = ''
            if (f && !validate(f)) onReplace(f)
          }}
        />
      </div>
    </section>
  )
}
