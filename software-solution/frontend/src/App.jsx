import { useState } from 'react'
import { predict } from './api.js'
import Viewport from './components/Viewport.jsx'
import Report from './components/Report.jsx'
import History from './components/History.jsx'

export default function App() {
  const [scan, setScan] = useState(null) // { file, url, width, height, loadedAt }
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])

  function selectFile(file) {
    // Free the previous preview unless the history list still shows it.
    if (scan && !history.some((h) => h.thumb === scan.url)) URL.revokeObjectURL(scan.url)
    setScan({ file, url: URL.createObjectURL(file), loadedAt: new Date() })
    setResult(null)
    setError('')
    setStatus('idle')
  }

  async function analyze() {
    setStatus('loading')
    setError('')
    try {
      const data = await predict(scan.file)
      setResult(data)
      setStatus('done')
      setHistory((h) => [{ ...data, thumb: scan.url, id: crypto.randomUUID() }, ...h].slice(0, 8))
    } catch (e) {
      setError(e.message === 'Failed to fetch' ? 'Serverul nu răspunde. Verificați că backend-ul Flask rulează.' : e.message)
      setStatus('error')
    }
  }

  return (
    <div className="app">
      <header className="bar">
        <span className="bar-title">Detecție cancer pulmonar</span>
        <span className="bar-note">Model provizoriu · rezultatele sunt simulate</span>
      </header>

      <main className="workspace">
        <Viewport
          scan={scan}
          busy={status === 'loading'}
          onFile={selectFile}
          onMeasure={(width, height) => setScan((s) => ({ ...s, width, height }))}
        />
        <Report
          scan={scan}
          status={status}
          result={result}
          error={error}
          onAnalyze={analyze}
          onReplace={selectFile}
        />
      </main>

      <History items={history} />

      <footer className="foot">
        Prototip de cercetare (MIRPR 2026–2027). Rezultatul nu reprezintă un diagnostic medical și
        trebuie interpretat de un medic radiolog.
      </footer>
    </div>
  )
}
