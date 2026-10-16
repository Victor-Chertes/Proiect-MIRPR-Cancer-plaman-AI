// CT volumes in the browser: a minimal NIfTI-1 reader/writer, a synthetic demo
// case and slice rendering for the three anatomical planes.
//
// A volume is { dims: [nx, ny, nz], spacing: [sx, sy, sz], data, slope, inter, range }
// where data is the raw typed array (x fastest, then y, then z).

const TYPES = {
  2: Uint8Array,
  4: Int16Array,
  8: Int32Array,
  16: Float32Array,
  64: Float64Array,
  256: Int8Array,
  512: Uint16Array,
  768: Uint32Array,
}

export const isNifti = (name) => /\.nii(\.gz)?$/i.test(name)

async function gunzip(buffer) {
  const stream = new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))
  return new Response(stream).arrayBuffer()
}

export async function readNifti(file) {
  let buffer = await file.arrayBuffer()
  const head = new Uint8Array(buffer, 0, 2)
  if (head[0] === 0x1f && head[1] === 0x8b) buffer = await gunzip(buffer)
  if (buffer.byteLength < 352) throw new Error('Fișierul NIfTI este incomplet.')

  const view = new DataView(buffer)
  let le = true
  if (view.getInt32(0, true) !== 348) {
    if (view.getInt32(0, false) !== 348) throw new Error('Fișierul nu este un NIfTI-1 valid.')
    le = false
  }
  const i16 = (o) => view.getInt16(o, le)
  const f32 = (o) => view.getFloat32(o, le)

  const ndim = i16(40)
  const dims = [i16(42), ndim >= 2 ? i16(44) : 1, ndim >= 3 ? i16(46) : 1]
  const Type = TYPES[i16(70)]
  if (!Type) throw new Error('Tip de date NIfTI neacceptat.')
  const spacing = [f32(80), f32(84), f32(88)].map((s) => (s > 0 && Number.isFinite(s) ? s : 1))
  const offset = Math.max(352, Math.round(f32(108)))
  const count = dims[0] * dims[1] * dims[2]
  if (offset + count * Type.BYTES_PER_ELEMENT > buffer.byteLength) {
    throw new Error('Datele volumului sunt incomplete.')
  }

  let data
  if (le && offset % Type.BYTES_PER_ELEMENT === 0) {
    data = new Type(buffer, offset, count)
  } else {
    // Unaligned or big-endian: copy element by element.
    data = new Type(count)
    const size = Type.BYTES_PER_ELEMENT
    const get = {
      1: (o) => (Type === Int8Array ? view.getInt8(o) : view.getUint8(o)),
      2: (o) => (Type === Int16Array ? view.getInt16(o, le) : view.getUint16(o, le)),
      4: (o) => (Type === Float32Array ? view.getFloat32(o, le) : Type === Int32Array ? view.getInt32(o, le) : view.getUint32(o, le)),
      8: (o) => view.getFloat64(o, le),
    }[size]
    for (let i = 0; i < count; i++) data[i] = get(offset + i * size)
  }

  const slope = f32(112) || 1
  const inter = f32(116) || 0
  return withRange({ dims, spacing, data, slope, inter })
}

function withRange(volume) {
  const { data, slope, inter } = volume
  let min = Infinity
  let max = -Infinity
  const step = Math.max(1, Math.floor(data.length / 200000))
  for (let i = 0; i < data.length; i += step) {
    const v = data[i]
    if (v < min) min = v
    if (v > max) max = v
  }
  return { ...volume, range: [min * slope + inter, max * slope + inter] }
}

// The NIfTI file sent to the API for the demo case, so it follows the same path
// as an uploaded scan.
export function writeNifti({ dims, spacing, data }) {
  const header = new ArrayBuffer(352)
  const v = new DataView(header)
  v.setInt32(0, 348, true)
  ;[3, dims[0], dims[1], dims[2], 1, 1, 1, 1].forEach((d, i) => v.setInt16(40 + i * 2, d, true))
  v.setInt16(70, 4, true) // int16
  v.setInt16(72, 16, true)
  ;[1, spacing[0], spacing[1], spacing[2], 1, 1, 1, 1].forEach((s, i) => v.setFloat32(76 + i * 4, s, true))
  v.setFloat32(108, 352, true)
  v.setFloat32(112, 1, true)
  v.setInt8(123, 10) // xyzt_units: mm, s
  new Uint8Array(header, 344, 4).set([0x6e, 0x2b, 0x31, 0]) // "n+1\0"
  return new Blob([header, data.buffer])
}

// Synthetic chest CT (Hounsfield units) with a nodule in the right lung and its
// segmentation mask. Deterministic, so the demo looks the same every time.
export function demoCase() {
  const [nx, ny, nz] = [160, 128, 96]
  const data = new Int16Array(nx * ny * nz)
  const mask = new Uint8Array(nx * ny * nz)
  let seed = 7
  const noise = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff
    return seed / 0x7fffffff - 0.5
  }
  const tumor = { x: 52, y: 58, z: 54, r: 9 }

  for (let z = 0; z < nz; z++) {
    const t = (z - nz / 2) / (nz / 2) // -1 (feet) .. 1 (head)
    const lungScale = Math.sqrt(Math.max(0, 1 - Math.pow((z - nz * 0.45) / (nz * 0.48), 2)))
    for (let y = 0; y < ny; y++) {
      for (let x = 0; x < nx; x++) {
        const i = x + y * nx + z * nx * ny
        const bx = (x - nx / 2) / 72
        const by = (y - ny / 2) / 52
        let hu = -1000 // air
        if (bx * bx + by * by < 1) {
          hu = 40 // soft tissue
          if (bx * bx + by * by > 0.82) hu = -90 // subcutaneous fat
          for (const side of [-1, 1]) {
            const lx = (x - (nx / 2 + side * 30)) / (24 * lungScale + 0.01)
            const ly = (y - (ny / 2 - 4)) / (36 * lungScale + 0.01)
            if (lx * lx + ly * ly < 1) {
              hu = -850
              // a few vessels running through the lung
              if (Math.abs(Math.sin(x * 0.35 + z * 0.2) * Math.cos(y * 0.3)) > 0.97) hu = -100
            }
          }
          const sx = x - nx / 2
          const sy = y - (ny / 2 + 38)
          if (sx * sx + sy * sy < 81) hu = 700 // vertebra
          const hx = x - (nx / 2 + 8)
          const hy = y - (ny / 2 + 4)
          if (t < 0.1 && hx * hx * 0.6 + hy * hy < 380) hu = 45 // heart
        }
        const dx = x - tumor.x
        const dy = y - tumor.y
        const dz = (z - tumor.z) * 1.6
        const d = Math.sqrt(dx * dx + dy * dy + dz * dz) + 2 * Math.sin(x * 0.9) * Math.cos(y * 0.7)
        if (d < tumor.r) {
          hu = 35
          mask[i] = 1
        }
        data[i] = Math.round(hu + noise() * 40)
      }
    }
  }

  const volume = withRange({ dims: [nx, ny, nz], spacing: [1.5, 1.5, 2.5], data, slope: 1, inter: 0 })
  const file = new File([writeNifti(volume)], 'caz-demo.nii', { type: 'application/octet-stream' })
  return { file, volume, mask, focus: tumor }
}

export const PLANES = {
  axial: { label: 'Axial', axis: 2 },
  coronal: { label: 'Coronal', axis: 1 },
  sagittal: { label: 'Sagital', axis: 0 },
}

// Display windows in HU; "auto" uses the full value range of the volume.
export const WINDOWS = {
  lung: { label: 'Pulmonar', center: -600, width: 1500 },
  mediastinum: { label: 'Mediastin', center: 40, width: 400 },
  auto: { label: 'Auto' },
}

export const looksLikeHU = (volume) => volume.range[0] < -500

export function sliceShape(volume, plane) {
  const [nx, ny, nz] = volume.dims
  const [sx, sy, sz] = volume.spacing
  if (plane === 'axial') return { cols: nx, rows: ny, aspect: (nx * sx) / (ny * sy) }
  if (plane === 'coronal') return { cols: nx, rows: nz, aspect: (nx * sx) / (nz * sz) }
  return { cols: ny, rows: nz, aspect: (ny * sy) / (nz * sz) }
}

// Draw one slice into an ImageData. Rows are flipped so anterior / superior
// end up at the top of the screen.
export function renderSlice(volume, mask, plane, index, win, showMask) {
  const [nx, ny] = volume.dims
  const { cols, rows } = sliceShape(volume, plane)
  const { data, slope, inter } = volume
  const [lo, hi] = win.width ? [win.center - win.width / 2, win.center + win.width / 2] : volume.range
  const scale = 255 / (hi - lo || 1)
  const image = new ImageData(cols, rows)
  const px = image.data

  for (let r = 0; r < rows; r++) {
    const flipped = rows - 1 - r
    for (let c = 0; c < cols; c++) {
      let i
      if (plane === 'axial') i = c + flipped * nx + index * nx * ny
      else if (plane === 'coronal') i = c + index * nx + flipped * nx * ny
      else i = index + c * nx + flipped * nx * ny
      const g = Math.max(0, Math.min(255, (data[i] * slope + inter - lo) * scale))
      const o = (r * cols + c) * 4
      if (showMask && mask && mask[i]) {
        px[o] = 0.45 * g + 0.55 * 255
        px[o + 1] = 0.45 * g + 0.55 * 70
        px[o + 2] = 0.45 * g + 0.55 * 60
      } else {
        px[o] = px[o + 1] = px[o + 2] = g
      }
      px[o + 3] = 255
    }
  }
  return image
}
