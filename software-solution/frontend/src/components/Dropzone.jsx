import { useRef, useState } from 'react'

const ACCEPTED = ['image/png', 'image/jpeg', 'image/bmp', 'image/tiff', 'image/webp']
const MAX_BYTES = 20 * 1024 * 1024

export default function Dropzone({ onFile }) {
  const input = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')

  function take(files) {
    const f = files?.[0]
    if (!f) return
    if (!ACCEPTED.includes(f.type)) {
      setError('Unsupported format. Use PNG, JPEG, BMP, TIFF or WebP.')
      return
    }
    if (f.size > MAX_BYTES) {
      setError('File is larger than 20 MB.')
      return
    }
    setError('')
    onFile(f)
  }

  return (
    <div
      className={`dropzone ${dragging ? 'dragging' : ''}`}
      role="button"
      tabIndex={0}
      onClick={() => input.current?.click()}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        take(e.dataTransfer.files)
      }}
    >
      <input
        ref={input}
        type="file"
        accept={ACCEPTED.join(',')}
        hidden
        onChange={(e) => {
          take(e.target.files)
          e.target.value = ''
        }}
      />
      <div className="drop-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
          strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 16V4" />
          <path d="m7 9 5-5 5 5" />
          <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
        </svg>
      </div>
      <p className="drop-title">
        Drop a CT scan here or <span className="link">browse</span>
      </p>
      <p className="drop-hint">PNG, JPEG, BMP, TIFF or WebP · up to 20 MB</p>
      {error && <p className="drop-error">{error}</p>}
    </div>
  )
}
