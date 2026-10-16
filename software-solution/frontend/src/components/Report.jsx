import { useRef } from 'react'
import { ACCEPT, SEXES, clinicalProblem, formatPercent, formatSize, validate } from '../format.js'

const KIND = { volume: 'Volum CT 3D (NIfTI)', dicom: 'CT (DICOM)', image: 'Felie CT 2D' }
const DISCLAIMER = 'Rezultat orientativ, generat automat. Nu înlocuiește biopsia și trebuie interpretat de un medic specialist.'

export default function Report({ scan, patient, onPatient, status, result, error, onAnalyze, onReplace }) {
  const input = useRef(null)
  const busy = status === 'loading'
  const problem = clinicalProblem(patient)
  const stale =
    result && (String(result.patient.age) !== patient.age || result.patient.sex !== patient.sex || result.patientId !== patient.id)
  const set = (field) => (e) => onPatient({ ...patient, [field]: e.target.value })

  return (
    <section className="report" aria-label="Raport">
      <h2 className="report-head">Raport</h2>

      <dl className="fields">
        <div>
          <dt>Investigație</dt>
          <dd>{scan ? KIND[scan.kind] : 'CT toracic'}</dd>
        </div>
        <div>
          <dt>Fișier</dt>
          <dd className="mono" title={scan?.file.name}>{scan ? scan.file.name : '—'}</dd>
        </div>
        <div>
          <dt>Dimensiuni</dt>
          <dd className="mono">
            {scan?.volume ? scan.volume.dims.join(' × ') : scan?.width ? `${scan.width} × ${scan.height} px` : '—'}
          </dd>
        </div>
        <div>
          <dt>Mărime</dt>
          <dd className="mono">{scan ? formatSize(scan.file.size) : '—'}</dd>
        </div>
      </dl>

      <fieldset className="patient" disabled={busy}>
        <legend>Date clinice</legend>
        <label className="field wide">
          <span>Cod pacient <em>(opțional)</em></span>
          <input value={patient.id} onChange={set('id')} placeholder="ex. P-0142" maxLength={32} autoComplete="off" />
        </label>
        <label className="field">
          <span>Vârstă (ani)</span>
          <input type="number" inputMode="numeric" min="0" max="120" step="1" value={patient.age} onChange={set('age')} required />
        </label>
        <div className="field" role="radiogroup" aria-label="Sex">
          <span>Sex</span>
          <div className="segmented light">
            {Object.entries(SEXES).map(([key, label]) => (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={patient.sex === key}
                className={patient.sex === key ? 'on' : ''}
                onClick={() => onPatient({ ...patient, sex: key })}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </fieldset>

      <div className="conclusion">
        <h3>Biomarkeri</h3>
        {busy ? (
          <div className="progress" role="status">
            <div className="progress-bar"><span /></div>
            <p className="pending">Se rulează modelul pe volum și datele clinice…</p>
          </div>
        ) : status === 'error' ? (
          <p className="error" role="alert">{error}</p>
        ) : status === 'done' && result ? (
          <>
            <ul className="markers">
              {result.biomarkers.map((b) => (
                <li key={b.name} className={b.positive ? 'positive' : 'negative'}>
                  <div className="marker-head">
                    <span className="marker-name">{b.name}</span>
                    <span className="mono">{formatPercent(b.probability)}</span>
                    <span className={`chip ${b.positive ? 'positive' : 'negative'}`}>{b.positive ? 'Pozitiv' : 'Negativ'}</span>
                  </div>
                  <div className="meter" title={`Prag de decizie: ${formatPercent(b.threshold)}`}>
                    <span className="meter-fill" style={{ width: formatPercent(b.probability) }} />
                    <span className="meter-threshold" style={{ left: formatPercent(b.threshold) }} />
                  </div>
                  <span className="marker-desc">{b.description}</span>
                </li>
              ))}
            </ul>
            {stale && <p className="warn">Datele clinice s-au modificat. Rulați din nou analiza.</p>}
            <p className="disclaimer">{DISCLAIMER}</p>
          </>
        ) : (
          <p className="pending">
            {!scan ? 'Încărcați o scanare sau deschideți cazul demo.' : problem || 'Gata pentru analiză.'}
          </p>
        )}
      </div>

      <div className="report-actions">
        <button className="btn primary" onClick={onAnalyze} disabled={!scan || busy || !!problem}>
          {busy ? (
            <>
              <span className="spinner" aria-hidden="true" /> Se analizează…
            </>
          ) : status === 'done' ? (
            'Rulează din nou analiza'
          ) : (
            'Rulează analiza'
          )}
        </button>
        {scan && (
          <button className="btn" onClick={() => input.current?.click()} disabled={busy}>
            Altă scanare
          </button>
        )}
        {status === 'done' && result && (
          <div className="export">
            <button className="btn" onClick={() => downloadJson(result, scan)}>Export JSON</button>
            <button className="btn" onClick={() => window.print()}>Export PDF</button>
          </div>
        )}
        <input
          ref={input}
          id="replace-file"
          type="file"
          accept={ACCEPT}
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

function downloadJson(result, scan) {
  const report = {
    generated: result.timestamp,
    model: result.model,
    patient: { id: result.patientId || null, age: result.patient.age, sex: result.patient.sex },
    scan: {
      filename: result.filename,
      type: scan.kind,
      dims: scan.volume?.dims ?? (scan.width ? [scan.width, scan.height] : null),
      spacing_mm: scan.volume?.spacing ?? null,
    },
    biomarkers: result.biomarkers,
    disclaimer: DISCLAIMER,
  }
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `raport-${result.patientId || 'pacient'}-${result.timestamp.slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
}
