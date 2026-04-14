import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Download, FileText, File, X, ChevronLeft, ChevronRight,
  ZoomIn, ZoomOut, Maximize2, Minimize2,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import * as pdfjsLib from 'pdfjs-dist'

// PDF.js worker — try local, fallback to inline (fake worker)
try {
  pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js'
} catch {
  // Fake worker mode — runs in main thread
  pdfjsLib.GlobalWorkerOptions.workerSrc = ''
}

// ── File type detection ─────────────────────────────────────

const PDF_EXTS = new Set(['.pdf'])
const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])
const PPTX_EXTS = new Set(['.pptx', '.ppt'])

function getExt(filename: string): string {
  const dot = filename.lastIndexOf('.')
  return dot >= 0 ? filename.slice(dot).toLowerCase() : ''
}

function getFileType(filename: string): 'pdf' | 'image' | 'pptx' | 'other' {
  const ext = getExt(filename)
  if (PDF_EXTS.has(ext)) return 'pdf'
  if (IMAGE_EXTS.has(ext)) return 'image'
  if (PPTX_EXTS.has(ext)) return 'pptx'
  return 'other'
}

// ── PDF Thumbnail ───────────────────────────────────────────

function PdfThumbnail({
  url,
  onLoaded,
}: {
  url: string
  onLoaded?: (pageCount: number) => void
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading')

  useEffect(() => {
    let cancelled = false
    setState('loading')

    const render = async () => {
      // Ensure absolute URL for pdf.js fetch
      const absUrl = url.startsWith('/') ? window.location.origin + url : url
      try {
        const loadingTask = pdfjsLib.getDocument({
          url: absUrl,
          disableAutoFetch: false,
          disableStream: false,
          isEvalSupported: false,
        })
        const pdf = await loadingTask.promise
        if (cancelled) return
        onLoaded?.(pdf.numPages)
        const page = await pdf.getPage(1)
        const viewport = page.getViewport({ scale: 0.5 })
        const canvas = canvasRef.current
        if (!canvas || cancelled) return
        canvas.width = viewport.width
        canvas.height = viewport.height
        const ctx = canvas.getContext('2d')!
        await page.render({ canvasContext: ctx, viewport }).promise
        if (!cancelled) setState('ok')
      } catch (e) {
        console.warn('PDF thumbnail error:', e)
        if (!cancelled) setState('error')
      }
    }
    render()
    return () => { cancelled = true }
  }, [url, onLoaded])

  if (state === 'error') {
    return (
      <div className="w-full h-24 flex flex-col items-center justify-center gap-1 text-[var(--text-muted)]">
        <FileText size={20} className="text-red-400/50" />
        <span className="text-[10px]">PDF</span>
      </div>
    )
  }

  return (
    <>
      {state === 'loading' && (
        <div className="w-full h-24 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      <canvas ref={canvasRef} className={`w-full h-auto rounded-md ${state === 'loading' ? 'hidden' : ''}`} />
    </>
  )
}

// ── Fullscreen PDF Viewer ───────────────────────────────────

function PdfFullViewer({ url, filename, onClose }: { url: string; filename: string; onClose: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [pdf, setPdf] = useState<pdfjsLib.PDFDocumentProxy | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [scale, setScale] = useState(1.2)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    pdfjsLib.getDocument(url).promise.then((doc) => {
      setPdf(doc)
      setTotalPages(doc.numPages)
    })
  }, [url])

  useEffect(() => {
    if (!pdf || !canvasRef.current) return
    let cancelled = false
    pdf.getPage(currentPage).then((page) => {
      if (cancelled) return
      const viewport = page.getViewport({ scale })
      const canvas = canvasRef.current!
      canvas.width = viewport.width
      canvas.height = viewport.height
      const ctx = canvas.getContext('2d')!
      page.render({ canvasContext: ctx, viewport })
    })
    return () => { cancelled = true }
  }, [pdf, currentPage, scale])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight' || e.key === ' ') setCurrentPage((p) => Math.min(p + 1, totalPages))
      if (e.key === 'ArrowLeft') setCurrentPage((p) => Math.max(p - 1, 1))
      if (e.key === '+' || e.key === '=') setScale((s) => Math.min(s + 0.2, 3))
      if (e.key === '-') setScale((s) => Math.max(s - 0.2, 0.4))
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose, totalPages])

  const toggleFullscreen = () => {
    if (!containerRef.current) return
    if (document.fullscreenElement) {
      document.exitFullscreen()
      setIsFullscreen(false)
    } else {
      containerRef.current.requestFullscreen()
      setIsFullscreen(true)
    }
  }

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex flex-col bg-[var(--bg-primary)]/95 backdrop-blur-sm"
    >
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 h-12 shrink-0 border-b border-[var(--border)]/40">
        <div className="flex items-center gap-3">
          <FileText size={16} className="text-[var(--accent)]" />
          <span className="text-sm text-[var(--text-primary)] font-medium truncate max-w-[300px]">{filename}</span>
          <span className="text-xs text-[var(--text-muted)]">{currentPage}/{totalPages}</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setScale((s) => Math.max(s - 0.2, 0.4))} className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors" title="Уменьшить">
            <ZoomOut size={16} />
          </button>
          <span className="text-xs text-[var(--text-muted)] w-12 text-center tabular-nums">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale((s) => Math.min(s + 0.2, 3))} className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors" title="Увеличить">
            <ZoomIn size={16} />
          </button>
          <button onClick={toggleFullscreen} className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors" title="Полный экран">
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <a href={url} download={filename} className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors" title="Скачать">
            <Download size={16} />
          </a>
          <button onClick={onClose} className="p-2.5 rounded-xl text-[var(--text-primary)] hover:text-red-400 hover:bg-red-500/10 transition-colors ml-2" title="Закрыть (Esc)">
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Canvas area — click outside canvas closes viewer */}
      <div
        className="flex-1 overflow-auto flex items-start justify-center p-4"
        onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      >
        <canvas ref={canvasRef} className="shadow-2xl rounded-sm" />
      </div>

      {/* Bottom nav */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 h-12 shrink-0 border-t border-[var(--border)]/40">
          <button
            onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            disabled={currentPage <= 1}
            className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] disabled:opacity-30 transition-colors"
          >
            <ChevronLeft size={18} />
          </button>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={totalPages}
              value={currentPage}
              onChange={(e) => {
                const v = parseInt(e.target.value)
                if (v >= 1 && v <= totalPages) setCurrentPage(v)
              }}
              className="w-12 text-center text-sm bg-[var(--bg-input)] border border-[var(--border)] rounded-md py-1 text-[var(--text-primary)] outline-none"
            />
            <span className="text-xs text-[var(--text-muted)]">из {totalPages}</span>
          </div>
          <button
            onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            disabled={currentPage >= totalPages}
            className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] disabled:opacity-30 transition-colors"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      )}
    </motion.div>
  )
}

// ── FilePreview Card (inline in chat) ───────────────────────

interface FilePreviewProps {
  url: string
  filename: string
}

export function FilePreview({ url, filename }: FilePreviewProps) {
  const [pageCount, setPageCount] = useState<number | null>(null)
  const [viewerOpen, setViewerOpen] = useState(false)
  const fileType = getFileType(filename)
  const displayName = filename.replace(/^[a-f0-9]{32}_/, '')  // strip UUID prefix

  const handlePageLoaded = useCallback((count: number) => setPageCount(count), [])

  if (fileType === 'pdf') {
    return (
      <>
        <div
          className="group/fp inline-block max-w-[280px] rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent)]/30 transition-all cursor-pointer my-2"
          onClick={() => setViewerOpen(true)}
        >
          {/* Thumbnail */}
          <div className="relative overflow-hidden bg-white/5 max-h-[200px]">
            <PdfThumbnail url={url} onLoaded={handlePageLoaded} />
            <div className="absolute inset-0 bg-gradient-to-t from-[var(--bg-card)] via-transparent to-transparent opacity-0 group-hover/fp:opacity-100 transition-opacity" />
          </div>

          {/* Info bar */}
          <div className="flex items-center gap-2 px-3 py-2">
            <FileText size={14} className="text-red-400 shrink-0" />
            <span className="text-xs text-[var(--text-primary)] truncate flex-1">{displayName}</span>
            {pageCount && (
              <span className="text-[10px] text-[var(--text-muted)] shrink-0">{pageCount} стр.</span>
            )}
            <Download size={12} className="text-[var(--text-muted)] shrink-0 opacity-0 group-hover/fp:opacity-100 transition-opacity" />
          </div>
        </div>

        <AnimatePresence>
          {viewerOpen && (
            <PdfFullViewer url={url} filename={displayName} onClose={() => setViewerOpen(false)} />
          )}
        </AnimatePresence>
      </>
    )
  }

  if (fileType === 'image') {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" className="block my-2">
        <img
          src={url}
          alt={displayName}
          loading="lazy"
          className="max-w-full max-h-[300px] rounded-xl border border-[var(--border)] object-contain hover:border-[var(--accent)]/30 transition-colors"
        />
      </a>
    )
  }

  // PPTX / Other — download card
  return (
    <a
      href={url}
      download={displayName}
      className="inline-flex items-center gap-3 px-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent)]/30 transition-all my-2 max-w-[300px]"
    >
      <div className="w-10 h-10 rounded-lg bg-[var(--accent)]/10 flex items-center justify-center shrink-0">
        <File size={18} className={fileType === 'pptx' ? 'text-orange-400' : 'text-[var(--accent)]'} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--text-primary)] truncate">{displayName}</p>
        <p className="text-[10px] text-[var(--text-muted)] uppercase">{getExt(filename).slice(1)} · Скачать</p>
      </div>
      <Download size={14} className="text-[var(--text-muted)] shrink-0" />
    </a>
  )
}
