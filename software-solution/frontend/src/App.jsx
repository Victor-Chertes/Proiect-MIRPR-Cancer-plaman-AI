import { useState } from 'react'
import { predict } from './api.js'
import { scanKind } from './format.js'
import { demoCase, readNifti } from './volume.js'
import Viewport from './components/Viewport.jsx'
import Report from './components/Report.jsx'
import History from './components/History.jsx'

const NO_PATIENT = { id: '', age: '', sex: '' }

export default function App() {
  // { file, kind: image | volume | dicom, url?, volume?, mask?, focus?, width?, height?, loadedAt }
  const [scan, setScan] = useState(null)
  const [reading, setReading] = useState(false)
  const [scanError, setScanError] = useState('')
  const [patient, setPatient] = useState(NO_PATIENT)
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])

  function show(next) {
    // Free the previous preview unless the history list still shows it.
    if (scan?.url && !history.some((h) => h.thumb === scan.url)) URL.revokeObjectURL(scan.url)
    setScan({ ...next, loadedAt: new Date() })
    setResult(null)
    setError('')
    setStatus('idle')
  }

  async function selectFile(file) {
    setScanError('')
    const kind = scanKind(file.name)
    if (kind === 'volume') {
      setReading(true)
      try {
        show({ file, kind, volume: await readNifti(file) })
      } catch (e) {
        setScanError(e.message)
      } finally {
        setReading(false)
      }
    } else {
      show({ file, kind, url: kind === 'image' ? URL.createObjectURL(file) : null })
    }
  }

  function loadDemo() {
    setScanError('')
    show({ kind: 'volume', ...demoCase(), demo: true })
    setPatient({ id: 'DEMO-001', age: '64', sex: 'M' })
  }

  async function loadMask(file) {
    setScanError('')
    try {
      const mask = await readNifti(file)
      if (mask.dims.join() !== scan.volume.dims.join()) {
        throw new Error(`Masca are dimensiunile ${mask.dims.join('×')}, volumul ${scan.volume.dims.join('×')}.`)
      }
      setScan((s) => ({ ...s, mask: mask.data, maskName: file.name }))
    } catch (e) {
      setScanError(e.message)
    }
  }

  async function analyze() {
    setStatus('loading')
    setError('')
    try {
      const data = await predict(scan.file, patient)
      const entry = { ...data, patientId: patient.id, thumb: scan.url, id: crypto.randomUUID() }
      setResult(entry)
      setStatus('done')
      setHistory((h) => [entry, ...h].slice(0, 8))
    } catch (e) {
      setError(e.message === 'Failed to fetch' ? 'Serverul nu răspunde. Verificați că backend-ul Flask rulează.' : e.message)
      setStatus('error')
    }
  }

  return (
    <div className="app">
      <header className="bar">
        <span className="bar-title">Biopsie virtuală · cancer pulmonar</span>
        <span className="bar-note">Model provizoriu · rezultatele sunt simulate</span>
      </header>

      <main className="workspace">
        <Viewport
          scan={scan}
          busy={status === 'loading'}
          reading={reading}
          error={scanError}
          onFile={selectFile}
          onDemo={loadDemo}
          onMask={loadMask}
          onMeasure={(width, height) => setScan((s) => ({ ...s, width, height }))}
        />
        <Report
          scan={scan}
          patient={patient}
          onPatient={setPatient}
          status={status}
          result={result}
          error={error}
          onAnalyze={analyze}
          onReplace={selectFile}
        />
      </main>

      <History items={history} />

      <footer className="foot">
        Prototip de cercetare (MIRPR 2026–2027). Rezultatul este orientativ, nu înlocuiește biopsia și
        trebuie interpretat de un medic specialist.
      </footer>
    </div>
  )
}
