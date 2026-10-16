export const LABELS = { POSITIVE: 'Pozitiv', NEGATIVE: 'Negativ' }

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

export const ACCEPTED = ['image/png', 'image/jpeg', 'image/bmp', 'image/tiff', 'image/webp']
const MAX_BYTES = 20 * 1024 * 1024

export function validate(file) {
  if (!ACCEPTED.includes(file.type)) return 'Format neacceptat. Folosiți PNG, JPEG, BMP, TIFF sau WebP.'
  if (file.size > MAX_BYTES) return 'Fișierul depășește 20 MB.'
  return ''
}
