export const SEXES = { M: 'Masculin', F: 'Feminin' }

export function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function formatTime(date) {
  return new Date(date).toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function formatDate(date) {
  return new Date(date).toLocaleDateString('ro-RO', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export const formatPercent = (p) => `${Math.round(p * 100)}%`

// Extensions, not MIME types: browsers report NIfTI and DICOM as empty or octet-stream.
export const ACCEPT = '.nii,.nii.gz,.dcm,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp'
const IMAGE = /\.(png|jpe?g|bmp|tiff?|webp)$/i
const MAX_BYTES = 200 * 1024 * 1024

export function scanKind(name) {
  if (/\.nii(\.gz)?$/i.test(name)) return 'volume'
  if (/\.dcm$/i.test(name)) return 'dicom'
  if (IMAGE.test(name)) return 'image'
  return null
}

export function validate(file) {
  if (!scanKind(file.name)) return 'Format neacceptat. Folosiți NIfTI (.nii, .nii.gz), DICOM (.dcm) sau o imagine.'
  if (file.size > MAX_BYTES) return 'Fișierul depășește 200 MB.'
  return ''
}

// Age and sex are required inputs of the model.
export function clinicalProblem({ age, sex }) {
  if (age === '') return 'Introduceți vârsta pacientului.'
  const n = Number(age)
  if (!Number.isInteger(n) || n < 0 || n > 120) return 'Vârsta trebuie să fie un număr întreg între 0 și 120.'
  if (!SEXES[sex]) return 'Selectați sexul pacientului.'
  return ''
}
