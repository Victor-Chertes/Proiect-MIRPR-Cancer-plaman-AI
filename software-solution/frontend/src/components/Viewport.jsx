import { useRef, useState } from 'react'
import { ACCEPTED, validate, formatSize, formatDate, formatTime } from '../format.js'

export default function Viewport({ scan, busy, onFile, onMeasure }) {
  const input = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')

  function take(files) {
    const f = files?.[0]
    if (!f) return
    const problem = validate(f)
    setError(problem)
    if (!problem) onFile(f)
  }

  return (
    <section
      className={`viewport ${dragging ? 'dragging' : ''} ${scan ? 'has-scan' : ''}`}
      aria-label="Imagine CT"
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
        accept={ACCEPTED.join(',')}
        hidden
        onChange={(e) => {
          take(e.target.files)
          e.target.value = ''
        }}
      />

      {scan ? (
        <>
          <img
            src={scan.url}
            alt={`Imagine CT: ${scan.file.name}`}
            onLoad={(e) => onMeasure(e.target.naturalWidth, e.target.naturalHeight)}
          />
          <div className="overlay tl">{scan.file.name}</div>
          <div className="overlay tr">{scan.width ? `${scan.width} × ${scan.height} px` : ''}</div>
          <div className="overlay bl">{formatSize(scan.file.size)}</div>
          <div className="overlay br">
            {formatDate(scan.loadedAt)} {formatTime(scan.loadedAt)}
          </div>
          {busy && <div className="sweep" aria-hidden="true" />}
        </>
      ) : (
        <div className="empty">
          <Crosshair />
          <p className="empty-title">Trageți aici o imagine CT</p>
          <p className="empty-hint">o felie axială a toracelui, PNG, JPEG, BMP, TIFF sau WebP, max. 20 MB</p>
          <button className="btn on-dark" onClick={() => input.current?.click()}>
            Alegeți un fișier
          </button>
          {error && <p className="empty-error" role="alert">{error}</p>}
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
