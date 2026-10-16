import { useState } from 'react'
import { predict } from './api.js'
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
      setHistory((h) =>
        [{ ...data, thumb: preview, id: crypto.randomUUID() }, ...h].slice(0, 5),
      )
    } catch (e) {
      setError(e.message === 'Failed to fetch' ? 'Serverul nu răspunde.' : e.message)
      setStatus('error')
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>Detecția cancerului pulmonar</h1>
        <p>Încărcați o imagine CT a toracelui pentru analiză.</p>
      </header>

      <main>
        {!file ? (
          <Dropzone onFile={selectFile} />
        ) : (
          <div className="card">
            <div className="scan">
              <img src={preview} alt="Imagine încărcată" />
            </div>

            <div className="toolbar">
              <span className="file-name" title={file.name}>
                {file.name} <span className="file-size">· {formatSize(file.size)}</span>
              </span>
              <div className="actions">
                <button className="btn" onClick={reset} disabled={status === 'loading'}>
                  {status === 'done' ? 'Altă imagine' : 'Elimină'}
                </button>
                {status !== 'done' && (
                  <button className="btn primary" onClick={analyze} disabled={status === 'loading'}>
                    {status === 'loading' ? 'Se analizează…' : 'Analizează'}
                  </button>
                )}
              </div>
            </div>

            {status === 'error' && <p className="error">{error}</p>}
            {status === 'done' && result && <ResultCard result={result} />}
          </div>
        )}

        {history.length > 0 && <History items={history} />}
      </main>

      <footer className="footer">
        Prototip de cercetare. Rezultatul nu reprezintă un diagnostic medical.
      </footer>
    </div>
  )
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
