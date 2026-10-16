import { useRef, useState } from 'react'
import { ACCEPT, validate, formatSize, formatDate, formatTime } from '../format.js'
import VolumeView from './VolumeView.jsx'

export default function Viewport({ scan, busy, reading, error, onFile, onDemo, onMask, onMeasure }) {
  const input = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [problem, setProblem] = useState('')

  function take(files) {
    const f = files?.[0]
    if (!f) return
    const p = validate(f)
    setProblem(p)
    if (!p) onFile(f)
  }

  const shownError = problem || error

  return (
    <section
      className={`viewport ${dragging ? 'dragging' : ''} ${scan ? 'has-scan' : ''}`}
      aria-label="Imagine CT"
      aria-busy={busy || reading}
      onDragOver={(e) => {
        e.preventDefault()
        if (!busy) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        if (!busy) take(e.dataTransfer.files)
      }}
    >
      <input
        ref={input}
        id="scan-file"
        type="file"
        accept={ACCEPT}
        hidden
        onChange={(e) => {
          take(e.target.files)
          e.target.value = ''
        }}
      />

      {reading ? (
        <div className="empty">
          <span className="spinner large" aria-hidden="true" />
          <p className="empty-title">Se citește volumul…</p>
        </div>
      ) : scan ? (
        <>
          {scan.kind === 'volume' ? (
            <VolumeView key={scan.loadedAt.getTime()} scan={scan} busy={busy} onMask={onMask} />
          ) : scan.kind === 'image' ? (
            <img
              src={scan.url}
              alt={`Imagine CT: ${scan.file.name}`}
              onLoad={(e) => onMeasure(e.target.naturalWidth, e.target.naturalHeight)}
            />
          ) : (
            <div className="empty">
              <p className="empty-title">Fișier DICOM încărcat</p>
              <p className="empty-hint">Previzualizarea DICOM nu este încă disponibilă. Analiza poate fi rulată.</p>
            </div>
          )}
          {scan.kind !== 'volume' && (
            <>
              <div className="overlay tl">{scan.file.name}</div>
              <div className="overlay tr">{scan.width ? `${scan.width} × ${scan.height} px` : ''}</div>
              <div className="overlay bl">{formatSize(scan.file.size)}</div>
              <div className="overlay br">
                {formatDate(scan.loadedAt)} {formatTime(scan.loadedAt)}
              </div>
            </>
          )}
          {shownError && <p className="viewport-error" role="alert">{shownError}</p>}
          {busy && (
            <div className="scanning" aria-hidden="true">
              <div className="sweep" />
              <div className="scanning-label">
                <span className="spinner" /> Analiză în curs
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="empty">
          <Crosshair />
          <p className="empty-title">Trageți aici o scanare CT</p>
          <p className="empty-hint">volum NIfTI (.nii, .nii.gz), fișier DICOM sau o felie axială ca imagine, max. 200 MB</p>
          <div className="empty-actions">
            <button className="btn on-dark" onClick={() => input.current?.click()}>
              Alegeți un fișier
            </button>
            <button className="btn on-dark" onClick={onDemo}>
              Caz demo
            </button>
          </div>
          {shownError && <p className="empty-error" role="alert">{shownError}</p>}
        </div>
      )}
    </section>
  )
}

function Crosshair() {
  return (
    <svg className="crosshair" viewBox="0 0 48 48" width="48" height="48" aria-hidden="true">
      <circle cx="24" cy="24" r="14" fill="none" stroke="currentColor" strokeWidth="1" />
      <path d="M24 2v12M24 34v12M2 24h12M34 24h12" stroke="currentColor" strokeWidth="1" />
    </svg>
  )
}
