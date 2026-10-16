import { useEffect, useRef, useState } from 'react'
import { PLANES, WINDOWS, looksLikeHU, renderSlice, sliceShape } from '../volume.js'

// Slice viewer for a 3D volume: plane switch, slice slider (or mouse wheel),
// display window and the segmentation mask overlay.
export default function VolumeView({ scan, busy, onMask }) {
  const { volume, mask, focus } = scan
  const canvas = useRef(null)
  const maskInput = useRef(null)
  const [plane, setPlane] = useState('axial')
  const [win, setWin] = useState(looksLikeHU(volume) ? 'lung' : 'auto')
  const [showMask, setShowMask] = useState(true)
  const [index, setIndex] = useState(() => {
    const [nx, ny, nz] = volume.dims
    const center = focus ?? { x: nx >> 1, y: ny >> 1, z: nz >> 1 }
    return { sagittal: center.x, coronal: center.y, axial: center.z }
  })

  const count = volume.dims[PLANES[plane].axis]
  const current = Math.min(index[plane], count - 1)
  const shape = sliceShape(volume, plane)

  useEffect(() => {
    // Draw at voxel resolution, then stretch to physical proportions (voxels are
    // often not cubic, e.g. 0.7 × 0.7 × 2.5 mm).
    const src = document.createElement('canvas')
    src.width = shape.cols
    src.height = shape.rows
    src.getContext('2d').putImageData(renderSlice(volume, mask, plane, current, WINDOWS[win], showMask), 0, 0)
    const c = canvas.current
    const scale = Math.max(1, Math.ceil(512 / Math.max(shape.cols, shape.rows)))
    c.width = shape.cols * scale
    c.height = Math.round((shape.cols * scale) / shape.aspect)
    const ctx = c.getContext('2d')
    ctx.imageSmoothingEnabled = false
    ctx.drawImage(src, 0, 0, c.width, c.height)
  }, [volume, mask, plane, current, win, showMask, shape.cols, shape.rows, shape.aspect])

  // React registers wheel listeners as passive, so preventDefault needs a native one.
  useEffect(() => {
    const c = canvas.current
    const onWheel = (e) => {
      e.preventDefault()
      const delta = e.deltaY > 0 ? 1 : -1
      setIndex((ix) => ({ ...ix, [plane]: Math.max(0, Math.min(count - 1, ix[plane] + delta)) }))
    }
    c.addEventListener('wheel', onWheel, { passive: false })
    return () => c.removeEventListener('wheel', onWheel)
  }, [plane, count])

  return (
    <div className="volume">
      <div className="volume-tools">
        <div className="segmented" role="group" aria-label="Plan">
          {Object.entries(PLANES).map(([key, p]) => (
            <button key={key} className={key === plane ? 'on' : ''} aria-pressed={key === plane} onClick={() => setPlane(key)}>
              {p.label}
            </button>
          ))}
        </div>
        <label className="tool">
          Fereastră
          <select value={win} onChange={(e) => setWin(e.target.value)}>
            {Object.entries(WINDOWS).map(([key, w]) => (
              <option key={key} value={key}>{w.label}</option>
            ))}
          </select>
        </label>
        {mask ? (
          <label className="tool">
            <input type="checkbox" checked={showMask} onChange={(e) => setShowMask(e.target.checked)} />
            Mască tumoră
          </label>
        ) : (
          <button className="tool link" onClick={() => maskInput.current?.click()} disabled={busy}>
            Încarcă mască
          </button>
        )}
        <input
          ref={maskInput}
          type="file"
          accept=".nii,.nii.gz"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0]
            e.target.value = ''
            if (f) onMask(f)
          }}
        />
      </div>

      <div className="volume-stage">
        <canvas
          ref={canvas}
          aria-label={`Felie ${PLANES[plane].label.toLowerCase()} ${current + 1} din ${count}`}
        />
      </div>

      <div className="volume-slider">
        <input
          type="range"
          min="0"
          max={count - 1}
          value={current}
          onChange={(e) => setIndex((ix) => ({ ...ix, [plane]: Number(e.target.value) }))}
          aria-label="Felie"
        />
        <span className="mono">
          {current + 1} / {count}
        </span>
      </div>
    </div>
  )
}
