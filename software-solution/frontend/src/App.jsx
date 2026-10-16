import { useEffect, useState } from 'react'
import { health, predict } from './api.js'
import Dropzone from './components/Dropzone.jsx'
import ResultCard from './components/ResultCard.jsx'
import History from './components/History.jsx'

export default function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])
  const [online, setOnline] = useState(null)

  useEffect(() => {
    health()
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
  }, [])

  // Free the current preview unless the history list still shows it.
  function releasePreview() {
    if (preview && !history.some((h) => h.thumb === preview)) URL.revokeObjectURL(preview)
  }

  function selectFile(f) {
    releasePreview()
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setResult(null)
    setError('')
    setStatus('idle')
  }

  function reset() {
    releasePreview()
    setFile(null)
    setPreview(null)
    setResult(null)
    setError('')
    setStatus('idle')
  }

  async function analyze() {
    if (!file) return
    setStatus('loading')
    setError('')
    try {
      const data = await predict(file)
      setResult(data)
      setStatus('done')
      setOnline(true)
      setHistory((h) =>
        [{ ...data, thumb: preview, id: crypto.randomUUID() }, ...h].slice(0, 6),
      )
    } catch (e) {
      setError(e.message === 'Failed to fetch' ? 'Could not reach the analysis server.' : e.message)
      setStatus('error')
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <LungIcon />
          </span>
          <span className="brand-name">PulmoScan</span>
        </div>
        <span className={`status-pill ${online === false ? 'off' : online ? 'on' : ''}`}>
          <span className="dot" />
          {online === null ? 'Connecting' : online ? 'Model online' : 'Server offline'}
        </span>
      </header>

      <main className="main">
        <section className="intro">
          <h1>Lung cancer screening</h1>
          <p>
            Upload a chest CT slice and the model will estimate whether it shows signs of a
            malignant nodule.
          </p>
        </section>

        <section className="workspace">
          {!file ? (
            <Dropzone onFile={selectFile} />
          ) : (
            <div className="panel">
              <div className="scan">
                <img src={preview} alt="Uploaded scan" />
                {status === 'loading' && <div className="scanline" />}
              </div>

              <div className="side">
                <div className="file-meta">
                  <span className="file-name" title={file.name}>{file.name}</span>
                  <span className="file-size">{formatSize(file.size)}</span>
                </div>

                {status === 'done' && result ? (
                  <ResultCard result={result} />
                ) : (
                  <div className="placeholder">
                    {status === 'loading' ? (
                      <>
                        <span className="spinner" />
                        <span>Analyzing scan…</span>
                      </>
                    ) : status === 'error' ? (
                      <span className="error">{error}</span>
                    ) : (
                      <span>Ready to analyze.</span>
                    )}
                  </div>
                )}

                <div className="actions">
                  {status !== 'done' && (
                    <button
                      className="btn primary"
                      onClick={analyze}
                      disabled={status === 'loading'}
                    >
                      {status === 'loading' ? 'Analyzing…' : status === 'error' ? 'Try again' : 'Analyze'}
                    </button>
                  )}
                  <button className="btn ghost" onClick={reset} disabled={status === 'loading'}>
                    {status === 'done' ? 'New scan' : 'Remove'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>

        {history.length > 0 && <History items={history} />}
      </main>

      <footer className="footer">
        Research prototype · not a medical device · results must be reviewed by a radiologist
      </footer>
    </div>
  )
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function LungIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v8" />
      <path d="M12 11c-1.6 0-2.6.9-3.4 2.6L7 18.4c-.4 1.2.5 2 1.6 1.6l1.6-.6c1.1-.4 1.8-1.5 1.8-2.7V11Z" />
      <path d="M12 11c1.6 0 2.6.9 3.4 2.6l1.6 4.8c.4 1.2-.5 2-1.6 1.6l-1.6-.6c-1.1-.4-1.8-1.5-1.8-2.7" />
    </svg>
  )
}
