import {
  useRef,
  useState,
  useEffect,
  useCallback,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from 'react'
import { Plus, Mic, MicOff, X, ChevronDown, ArrowUp } from 'lucide-react'
import { uploadFile } from '@/api/client'
import { fileIcon } from '@/utils/time'
import { AnimatePresence, motion } from 'framer-motion'
import { useToast } from '@/components/ui/Toast'

const MODEL_OPTIONS = [
  { id: 'sonnet-4-6', label: 'Sonnet 4.6', desc: 'Быстрый и умный' },
  { id: 'opus-4-6', label: 'Opus 4.6', desc: 'Максимальный интеллект' },
  { id: 'haiku-4-5', label: 'Haiku 4.5', desc: 'Сверхбыстрый' },
]

interface AttachedFile {
  name: string
  path: string
}

interface ChatInputProps {
  onSend: (text: string, files: string[], model: string) => void
  disabled?: boolean
  conversationId?: string
  placeholder?: string
  initialModel?: string
}

export function ChatInput({
  onSend,
  disabled = false,
  conversationId,
  placeholder = 'Чем могу помочь сегодня?',
  initialModel,
}: ChatInputProps) {
  const { error: showError } = useToast()
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [selectedModel, setSelectedModel] = useState(() => {
    const modelId = initialModel ?? localStorage.getItem('neura_model')
    return MODEL_OPTIONS.find((m) => m.id === modelId) ?? MODEL_OPTIONS[0]
  })
  const [modelOpen, setModelOpen] = useState(false)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<BlobPart[]>([])
  const modelRef = useRef<HTMLDivElement>(null)
  const uploadAbortRef = useRef<AbortController | null>(null)

  // Restore draft
  useEffect(() => {
    const draft = conversationId
      ? (sessionStorage.getItem(`draft_${conversationId}`) ?? '')
      : ''
    setText(draft)
  }, [conversationId])

  // Save draft
  useEffect(() => {
    if (conversationId) {
      sessionStorage.setItem(`draft_${conversationId}`, text)
    }
  }, [text, conversationId])

  // Auto-resize textarea — grows up to 50vh, no internal scrollbar
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    const maxH = Math.floor(window.innerHeight * 0.5)
    el.style.height = `${Math.min(el.scrollHeight, maxH)}px`
  }, [text])

  // Focus
  useEffect(() => {
    if (!disabled) textareaRef.current?.focus()
  }, [conversationId, disabled])

  // Close model dropdown on outside click
  useEffect(() => {
    if (!modelOpen) return
    const handler = (e: MouseEvent) => {
      if (modelRef.current && !modelRef.current.contains(e.target as Node)) {
        setModelOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [modelOpen])

  // Prefill from welcome cards (legacy event)
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.text) setText(detail.text)
    }
    document.addEventListener('neura:prefill-input', handler)
    return () => document.removeEventListener('neura:prefill-input', handler)
  }, [])

  const doSend = useCallback(() => {
    const trimmed = text.trim()
    if ((!trimmed && attachedFiles.length === 0) || disabled || isUploading) return

    onSend(trimmed, attachedFiles.map((f) => f.path), selectedModel.id)
    setText('')
    setAttachedFiles([])
    if (conversationId) sessionStorage.removeItem(`draft_${conversationId}`)
    textareaRef.current?.focus()
  }, [text, attachedFiles, disabled, isUploading, onSend, conversationId])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      doSend()
    }
  }

  const cancelUpload = useCallback(() => {
    if (uploadAbortRef.current) {
      uploadAbortRef.current.abort()
      uploadAbortRef.current = null
      setIsUploading(false)
    }
  }, [])

  const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB

  const uploadFiles = useCallback(async (selected: File[]) => {
    if (selected.length === 0) return

    // Client-side size check
    const oversized = selected.filter((f) => f.size > MAX_FILE_SIZE)
    if (oversized.length > 0) {
      const names = oversized.map((f) => f.name).join(', ')
      showError(`Файлы превышают 100MB: ${names}`)
      selected = selected.filter((f) => f.size <= MAX_FILE_SIZE)
      if (selected.length === 0) return
    }

    const controller = new AbortController()
    uploadAbortRef.current = controller
    setIsUploading(true)
    try {
      const results = await Promise.allSettled(
        selected.map((f) => uploadFile(f, controller.signal)),
      )
      const succeeded: AttachedFile[] = []
      const failedNames: string[] = []
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') {
          succeeded.push({ name: r.value.filename, path: r.value.path })
        } else {
          if ((r.reason as Error)?.name !== 'AbortError') {
            failedNames.push(selected[i].name)
          }
        }
      })
      if (succeeded.length > 0) {
        setAttachedFiles((prev) => [...prev, ...succeeded])
      }
      if (failedNames.length > 0) {
        showError(`Не удалось загрузить: ${failedNames.join(', ')}`)
      }
    } finally {
      uploadAbortRef.current = null
      setIsUploading(false)
    }
  }, [showError])

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? [])
    e.target.value = ''
    await uploadFiles(selected)
  }

  const removeFile = (idx: number) => {
    setAttachedFiles((prev) => prev.filter((_f, i) => i !== idx))
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }
  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    await uploadFiles(Array.from(e.dataTransfer.files))
  }

  // Clipboard paste (images/files from buffer)
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return
    const files: File[] = []
    for (const item of Array.from(items)) {
      if (item.kind === 'file') {
        const f = item.getAsFile()
        if (f) files.push(f)
      }
    }
    if (files.length > 0) {
      e.preventDefault()
      await uploadFiles(files)
    }
  }, [uploadFiles])

  // Voice recording
  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop()
      setIsRecording(false)
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      audioChunksRef.current = []

      recorder.ondataavailable = (e) => {
        audioChunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const file = new File([blob], `voice_${Date.now()}.webm`, { type: 'audio/webm' })
        await uploadFiles([file])
      }

      recorder.start()
      setIsRecording(true)
    } catch {
      console.error('Microphone access denied')
      showError('Нет доступа к микрофону')
    }
  }

  return (
    <div
      className="relative px-4 pb-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2 shrink-0 max-w-3xl mx-auto w-full"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none rounded-2xl mx-4">
          <div className="border-2 border-dashed border-[var(--accent)] rounded-2xl px-8 py-4 bg-[var(--accent)]/10 text-[var(--accent)] text-sm font-medium">
            Перетащите файлы сюда
          </div>
        </div>
      )}

      {/* File chips */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2 max-h-[120px] overflow-y-auto">
          {attachedFiles.map((f, i) => (
            <div
              key={i}
              className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-md bg-[var(--bg-input)] border border-[var(--border)] text-[var(--text-secondary)]"
            >
              <span>{fileIcon(f.name)}</span>
              <span className="max-w-[140px] truncate">{f.name}</span>
              <button
                onClick={() => removeFile(i)}
                aria-label="Удалить файл"
                title="Удалить файл"
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors ml-0.5 flex-shrink-0"
              >
                <X size={11} />
              </button>
            </div>
          ))}
          {isUploading && (
            <div className="flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-[var(--bg-input)] border border-[var(--accent)]/30 text-[var(--text-muted)]">
              <span className="inline-block w-3 h-3 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
              <span>Загрузка...</span>
              <button
                onClick={cancelUpload}
                aria-label="Отменить загрузку"
                title="Отменить загрузку"
                className="ml-1 text-[var(--text-muted)] hover:text-red-400 transition-colors flex-shrink-0"
              >
                <X size={11} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Input box — Claude.ai style */}
      <div
        className={`flex flex-col bg-[var(--bg-card)] border rounded-2xl transition-colors ${
          isDragging
            ? 'border-[var(--accent)]'
            : 'border-[var(--border)]'
        }`}
      >
        {/* Textarea area */}
        <textarea
          ref={textareaRef}
          data-chat-input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          className="w-full bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] resize-none outline-none leading-6 px-4 pt-3 pb-1 min-h-[36px] focus:outline-none focus:ring-0 focus:shadow-none"
          style={{ boxShadow: 'none' }}
        />
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Bottom controls row */}
        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          {/* Left: attach */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            title="Прикрепить файл"
            aria-label="Прикрепить файл"
            className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors disabled:opacity-30 rounded-md hover:bg-[var(--bg-hover)]"
          >
            <Plus size={18} strokeWidth={1.5} />
          </button>

          {/* Right: model selector + voice */}
          <div className="flex items-center gap-1">
            {/* Model selector */}
            <div className="relative" ref={modelRef}>
              <button
                onClick={() => setModelOpen((v) => !v)}
                aria-label="Выбрать модель"
                title="Выбрать модель"
                className="flex items-center gap-1 px-2 py-1 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] rounded-md transition-colors"
              >
                <span>{selectedModel.label}</span>
                <ChevronDown
                  size={11}
                  className={`transition-transform duration-150 ${modelOpen ? 'rotate-180' : ''}`}
                />
              </button>

              <AnimatePresence>
                {modelOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 4 }}
                    transition={{ duration: 0.12 }}
                    className="absolute right-0 bottom-full mb-1.5 w-48 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] shadow-lg shadow-black/30 z-50 overflow-hidden"
                  >
                    {MODEL_OPTIONS.map((model) => (
                      <button
                        key={model.id}
                        onClick={() => {
                          setSelectedModel(model)
                          localStorage.setItem('neura_model', model.id)
                          setModelOpen(false)
                        }}
                        className={`flex flex-col w-full px-3 py-2 text-left transition-colors ${
                          selectedModel.id === model.id
                            ? 'bg-[var(--accent)]/10'
                            : 'hover:bg-[var(--bg-hover)]'
                        }`}
                      >
                        <span
                          className={`text-xs font-medium ${
                            selectedModel.id === model.id
                              ? 'text-[var(--text-primary)]'
                              : 'text-[var(--text-secondary)]'
                          }`}
                        >
                          {model.label}
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">
                          {model.desc}
                        </span>
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Voice */}
            <button
              type="button"
              onClick={toggleRecording}
              disabled={disabled}
              title={isRecording ? 'Остановить запись' : 'Голосовое сообщение'}
              aria-label={isRecording ? 'Остановить запись' : 'Голосовое сообщение'}
              className={`p-1.5 rounded-md transition-colors disabled:opacity-30 ${
                isRecording
                  ? 'text-red-400 pulse-ring'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
              }`}
            >
              {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
            </button>

            {/* Send */}
            <button
              type="button"
              onClick={doSend}
              disabled={disabled || (!text.trim() && attachedFiles.length === 0)}
              title="Отправить"
              aria-label="Отправить"
              className={`p-1 rounded-full transition-all duration-150 ease-in-out disabled:opacity-30 ${
                text.trim() || attachedFiles.length > 0
                  ? 'bg-[var(--accent)] text-white hover:brightness-110'
                  : 'bg-transparent text-[var(--text-muted)]'
              }`}
            >
              <ArrowUp size={18} strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
