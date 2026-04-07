/**
 * Get file type label by extension (no emoji — brand consistency).
 */
export function fileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    pdf: 'PDF', doc: 'DOC', docx: 'DOC', txt: 'TXT',
    xls: 'XLS', xlsx: 'XLS', csv: 'CSV',
    ppt: 'PPT', pptx: 'PPT',
    jpg: 'IMG', jpeg: 'IMG', png: 'IMG', gif: 'GIF', webp: 'IMG', svg: 'SVG',
    mp3: 'MP3', wav: 'WAV', ogg: 'OGG', webm: 'WEBM',
    mp4: 'MP4', avi: 'AVI', mov: 'MOV',
    zip: 'ZIP', rar: 'RAR', tar: 'TAR', gz: 'GZ',
    py: 'PY', js: 'JS', ts: 'TS', html: 'HTML', css: 'CSS', json: 'JSON',
  }
  return map[ext] ?? (ext.toUpperCase() || 'FILE')
}

/**
 * Format an ISO timestamp as a short relative string in Russian.
 */
export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60_000)
  if (diffMin < 1) return 'только что'
  if (diffMin < 60) return `${diffMin}м`
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return `${diffHours}ч`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return 'вчера'
  if (diffDays < 7) return `${diffDays}д`
  return date.toLocaleDateString('ru', { day: 'numeric', month: 'short' })
}
