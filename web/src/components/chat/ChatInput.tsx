import {
  useRef,
  useState,
  useEffect,
  useCallback,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from 'react'
import { createPortal } from 'react-dom'
import { Plus, Mic, MicOff, X, ChevronDown, ArrowUp, Brain, Zap, Search } from 'lucide-react'
import { uploadFile } from '@/api/client'
import { api } from '@/api/client'
import { fileIcon } from '@/utils/time'
import { motion } from 'framer-motion'
import { useToast } from '@/components/ui/Toast'

interface ModelOption {
  id: string
  label: string
  desc: string
  price?: string
  tier?: string
}

const CLAUDE_MODELS: ModelOption[] = [
  { id: 'sonnet-4-6', label: 'Sonnet 4.6', desc: 'Быстрый и умный' },
  { id: 'opus-4-6', label: 'Opus 4.6', desc: 'Максимальный интеллект' },
  { id: 'haiku-4-5', label: 'Haiku 4.5', desc: 'Сверхбыстрый' },
]

const OPENCODE_MODELS: ModelOption[] = [
  { id: 'openrouter/deepseek/deepseek-chat-v3.1', label: 'DeepSeek V3.1', desc: '$0.27/1M', tier: 'budget' },
  { id: 'openrouter/deepseek/deepseek-v3.2', label: 'DeepSeek V3.2', desc: '$0.27/1M', tier: 'budget' },
  { id: 'openrouter/google/gemini-2.5-flash', label: 'Gemini 2.5 Flash', desc: '$0.15/1M', tier: 'budget' },
  { id: 'openrouter/google/gemini-2.5-pro', label: 'Gemini 2.5 Pro', desc: '$1.25/1M', tier: 'standard' },
  { id: 'openrouter/anthropic/claude-sonnet-4', label: 'Claude Sonnet 4 API', desc: '$3/1M', tier: 'premium' },
]

const YANDEX_MODELS: ModelOption[] = [
  { id: 'yandexgpt-lite', label: 'YandexGPT Lite', desc: 'Быстрый и дешёвый', tier: 'budget' },
  { id: 'yandexgpt', label: 'YandexGPT', desc: 'Стандартный', tier: 'standard' },
  { id: 'yandexgpt-pro', label: 'YandexGPT Pro', desc: 'Максимальное качество', tier: 'premium' },
]

const ENGINES = [
  { id: 'claude', label: 'Claude Code', Icon: Brain, disabled: false },
  { id: 'opencode', label: 'OpenCode', Icon: Zap, disabled: false },
  { id: 'yandex', label: 'YandexGPT', Icon: Search, disabled: true },
]

function getModelsForEngine(engine: string): ModelOption[] {
  switch (engine) {
    case 'opencode': return OPENCODE_MODELS
    case 'yandex': return YANDEX_MODELS
    default: return CLAUDE_MODELS
  }
}

function getEngineIconComponent(engine: string) {
  return ENGINES.find(e => e.id === engine)?.Icon ?? Brain
}

interface AttachedFile {
  name: string
  path: string
}

interface ChatInputProps {
  onSend: (text: string, files: string[], model: string, engine?: string) => void
  disabled?: boolean
  conversationId?: string
  placeholder?: string
  initialModel?: string
  initialEngine?: string
}

export function ChatInput({
  onSend,
  disabled = false,
  conversationId,
  placeholder = 'Чем могу помочь сегодня?',
  initialModel,
  initialEngine,
}: ChatInputProps) {
  const { error: showError } = useToast()
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [isRecording, setIsRecording] = useState(false)

  // Engine state — per conversation (new chat always starts with claude)
  const [currentEngine, setCurrentEngine] = useState(() => {
    if (initialEngine) return initialEngine
    if (conversationId) {
      return sessionStorage.getItem(`engine_${conversationId}`) ?? 'claude'
    }
    return 'claude'
  })
  const [engineMenuOpen, setEngineMenuOpen] = useState(false)

  // Model state — depends on engine
  const models = getModelsForEngine(currentEngine)
  const [selectedModel, setSelectedModel] = useState(() => {
    const modelId = initialModel ?? localStorage.getItem('neura_model')
    return models.find((m) => m.id === modelId) ?? models[0]
  })
  const [modelOpen, setModelOpen] = useState(false)

  // Sync model when engine changes
  useEffect(() => {
    const newModels = getModelsForEngine(currentEngine)
    const savedModelId =
      localStorage.getItem(`neura_model_${currentEngine}`) ??
      localStorage.getItem('neura_model')
    setSelectedModel(
      newModels.find(m => m.id === savedModelId) ?? newModels[0]
    )
  }, [currentEngine])

  // Sync model when initialModel prop changes (conversation switch)
  useEffect(() => {
    const currentModels = getModelsForEngine(currentEngine)
    if (initialModel) {
      const found = currentModels.find((m) => m.id === initialModel)
      if (found) setSelectedModel(found)
    } else {
      const savedId = localStorage.getItem('neura_model')
      const found = currentModels.find((m) => m.id === savedId)
      if (found) setSelectedModel(found)
    }
  }, [initialModel])

  // Reset engine when conversation changes
  useEffect(() => {
    if (conversationId) {
      const saved = sessionStorage.getItem(`engine_${conversationId}`)
      setCurrentEngine(saved ?? 'claude')
    } else {
      setCurrentEngine('claude') // new chat = always claude
    }
  }, [conversationId])

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<BlobPart[]>([])
  const modelBtnRef = useRef<HTMLButtonElement>(null)
  const modelPopupRef = useRef<HTMLDivElement>(null)
  const engineBtnRef = useRef<HTMLButtonElement>(null)
  const enginePopupRef = useRef<HTMLDivElement>(null)
  const uploadAbortRef = useRef<AbortController | null>(null)

  // Popup positioning
  const [modelPopupPos, setModelPopupPos] = useState({ bottom: 0, right: 0 })
  const [enginePopupPos, setEnginePopupPos] = useState({ bottom: 0, left: 0 })

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

  // Auto-resize textarea
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

  // Close dropdowns on outside click — check both button AND popup refs
  useEffect(() => {
    if (!modelOpen && !engineMenuOpen) return
    const handler = (e: MouseEvent) => {
      const target = e.target as Node
      if (modelOpen) {
        const inBtn = modelBtnRef.current?.contains(target)
        const inPopup = modelPopupRef.current?.contains(target)
        if (!inBtn && !inPopup) setModelOpen(false)
      }
      if (engineMenuOpen) {
        const inBtn = engineBtnRef.current?.contains(target)
        const inPopup = enginePopupRef.current?.contains(target)
        if (!inBtn && !inPopup) setEngineMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [modelOpen, engineMenuOpen])

  // Prefill from welcome cards
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.text) setText(detail.text)
    }
    document.addEventListener('neura:prefill-input', handler)
    return () => document.removeEventListener('neura:prefill-input', handler)
  }, [])

  const switchEngine = useCallback((engineId: string) => {
    setCurrentEngine(engineId)
    if (conversationId) {
      sessionStorage.setItem(`engine_${conversationId}`, engineId)
    }
    setEngineMenuOpen(false)
    // Save to API for backend routing
    api.post('/api/engine', { engine: engineId }).catch(() => {})
  }, [conversationId])

  const selectModel = useCallback((model: ModelOption) => {
    setSelectedModel(model)
    if (conversationId) {
      sessionStorage.setItem(`model_${conversationId}`, model.id)
    }
    setModelOpen(false)
    // Save to API for backend routing
    if (currentEngine === 'opencode') {
      api.post('/api/engine', { opencode_model: model.id }).catch(() => {})
    }
  }, [currentEngine, conversationId])

  const doSend = useCallback(() => {
    const trimmed = text.trim()
    if ((!trimmed && attachedFiles.length === 0) || disabled || isUploading) return
    onSend(trimmed, attachedFiles.map((f) => f.path), selectedModel.id, currentEngine)
    setText('')
    setAttachedFiles([])
    if (conversationId) sessionStorage.removeItem(`draft_${conversationId}`)
    textareaRef.current?.focus()
  }, [text, attachedFiles, disabled, isUploading, onSend, conversationId, selectedModel])

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

  const MAX_FILE_SIZE = 100 * 1024 * 1024

  const uploadFiles = useCallback(async (selected: File[]) => {
    if (selected.length === 0) return
    const oversized = selected.filter((f) => f.size > MAX_FILE_SIZE)
    if (oversized.length > 0) {
      showError(`Файлы превышают 100MB: ${oversized.map(f => f.name).join(', ')}`)
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
      if (succeeded.length > 0) setAttachedFiles((prev) => [...prev, ...succeeded])
      if (failedNames.length > 0) showError(`Не удалось загрузить: ${failedNames.join(', ')}`)
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
  const removeFile = (idx: number) => setAttachedFiles((prev) => prev.filter((_f, i) => i !== idx))

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true) }
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false) }
  const handleDrop = async (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false); await uploadFiles(Array.from(e.dataTransfer.files)) }

  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return
    const files: File[] = []
    for (const item of Array.from(items)) {
      if (item.kind === 'file') { const f = item.getAsFile(); if (f) files.push(f) }
    }
    if (files.length > 0) { e.preventDefault(); await uploadFiles(files) }
  }, [uploadFiles])

  const toggleRecording = async () => {
    if (isRecording) { mediaRecorderRef.current?.stop(); setIsRecording(false); return }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      audioChunksRef.current = []
      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await uploadFiles([new File([blob], `voice_${Date.now()}.webm`, { type: 'audio/webm' })])
      }
      recorder.start()
      setIsRecording(true)
    } catch {
      showError('Нет доступа к микрофону')
    }
  }

  // Calculate popup position for model selector
  const openModelMenu = () => {
    if (modelBtnRef.current) {
      const rect = modelBtnRef.current.getBoundingClientRect()
      setModelPopupPos({
        bottom: window.innerHeight - rect.top + 6,
        right: window.innerWidth - rect.right,
      })
    }
    setModelOpen(v => !v)
  }

  const openEngineMenu = () => {
    if (engineBtnRef.current) {
      const rect = engineBtnRef.current.getBoundingClientRect()
      setEnginePopupPos({
        bottom: window.innerHeight - rect.top + 6,
        left: rect.left,
      })
    }
    setEngineMenuOpen(v => !v)
  }

  return (
    <div
      className="relative px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2 shrink-0 max-w-3xl mx-auto w-full"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none rounded-2xl mx-4">
          <div className="border-2 border-dashed border-[var(--accent)] rounded-2xl px-8 py-4 bg-[var(--accent)]/10 text-[var(--accent)] text-sm font-medium">
            Перетащите файлы сюда
          </div>
        </div>
      )}

      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2 max-h-[120px] overflow-y-auto">
          {attachedFiles.map((f, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-md liquid-glass text-[var(--text-secondary)]">
              <span>{fileIcon(f.name)}</span>
              <span className="max-w-[140px] truncate">{f.name}</span>
              <button onClick={() => removeFile(i)} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors ml-0.5 flex-shrink-0"><X size={11} /></button>
            </div>
          ))}
          {isUploading && (
            <div className="flex items-center gap-1 text-xs px-2 py-1 rounded-md liquid-glass border-[var(--accent)]/30 text-[var(--text-muted)]">
              <span className="inline-block w-3 h-3 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
              <span>Загрузка...</span>
              <button onClick={cancelUpload} className="ml-1 text-[var(--text-muted)] hover:text-red-400 transition-colors flex-shrink-0"><X size={11} /></button>
            </div>
          )}
        </div>
      )}

      <div className={`flex flex-col liquid-glass-input rounded-[20px] outline-none ${isDragging ? '!border-[var(--accent)]' : ''}`}>
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
          className="w-full bg-transparent text-[15px] text-[var(--text-primary)] placeholder-[var(--text-muted)] resize-none outline-none leading-6 px-4 pt-3.5 pb-1.5 min-h-[44px] focus:outline-none focus:ring-0 focus:shadow-none"
          style={{ boxShadow: 'none' }}
        />
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileChange} />

        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          {/* Left: attach + engine */}
          <div className="flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              title="Прикрепить файл"
              className="p-2 md:p-1.5 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors disabled:opacity-30 rounded-md hover:bg-[var(--bg-hover)] min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 flex items-center justify-center"
            >
              <Plus size={18} strokeWidth={1.5} />
            </button>

            {/* Engine switcher */}
            <button
              ref={engineBtnRef}
              type="button"
              onClick={openEngineMenu}
              title="Сменить движок"
              className="flex items-center gap-1 px-2 py-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] rounded-md transition-colors"
            >
              {(() => { const Icon = getEngineIconComponent(currentEngine); return <Icon size={14} /> })()}
            </button>
          </div>

          {/* Right: model selector + voice + send */}
          <div className="flex items-center gap-1">
            <button
              ref={modelBtnRef}
              onClick={openModelMenu}
              title="Выбрать модель"
              className="flex items-center gap-1 px-2 py-1 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] rounded-md transition-colors"
            >
              <span>{selectedModel.label}</span>
              <ChevronDown size={11} className={`transition-transform duration-150 ${modelOpen ? 'rotate-180' : ''}`} />
            </button>

            <button
              type="button"
              onClick={toggleRecording}
              disabled={disabled}
              title={isRecording ? 'Остановить запись' : 'Голосовое сообщение'}
              className={`p-2 md:p-1.5 rounded-md transition-colors disabled:opacity-30 min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 flex items-center justify-center ${
                isRecording ? 'text-red-400 pulse-ring' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
              }`}
            >
              {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
            </button>

            <button
              type="button"
              onClick={doSend}
              disabled={disabled || (!text.trim() && attachedFiles.length === 0)}
              title="Отправить"
              className={`p-2 md:p-1 rounded-full transition-all duration-150 ease-in-out disabled:opacity-30 min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 flex items-center justify-center ${
                text.trim() || attachedFiles.length > 0
                  ? 'bg-[var(--accent)]/80 text-white backdrop-blur-lg border border-white/15 shadow-[inset_0_1px_0_rgba(255,255,255,0.2)] hover:bg-[var(--accent)]/90'
                  : 'bg-transparent text-[var(--text-muted)]'
              }`}
            >
              <ArrowUp size={18} strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>

      {/* Model popup — portal to body */}
      {modelOpen && createPortal(
        <div
          ref={modelPopupRef}
          className="fixed z-[9999]"
          style={{ bottom: modelPopupPos.bottom, right: modelPopupPos.right }}
        >
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.12 }}
            className="w-56 liquid-glass-popup rounded-xl overflow-hidden shadow-xl"
          >
            <div className="px-3 py-1.5 text-[10px] text-[var(--text-muted)] uppercase tracking-wider border-b border-[var(--border)]/50">
              {ENGINES.find(e => e.id === currentEngine)?.label ?? 'Модели'}
            </div>
            {models.map((model) => (
              <button
                key={model.id}
                onClick={() => selectModel(model)}
                className={`flex items-center gap-2 w-full px-3 py-2 text-left transition-colors ${
                  selectedModel.id === model.id ? 'bg-[var(--accent)]/10' : 'hover:bg-[var(--bg-hover)]'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <span className={`text-xs font-medium ${
                    selectedModel.id === model.id ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'
                  }`}>{model.label}</span>
                  <span className="block text-[10px] text-[var(--text-muted)]">{model.desc}</span>
                </div>
                {model.tier && (
                  <span className={`text-[9px] px-1 py-0.5 rounded shrink-0 ${
                    model.tier === 'free' ? 'bg-green-500/10 text-green-500' :
                    model.tier === 'budget' ? 'bg-blue-500/10 text-blue-500' :
                    model.tier === 'standard' ? 'bg-yellow-500/10 text-yellow-500' :
                    'bg-purple-500/10 text-purple-500'
                  }`}>{model.tier}</span>
                )}
              </button>
            ))}
          </motion.div>
        </div>,
        document.body
      )}

      {/* Engine popup — portal to body */}
      {engineMenuOpen && createPortal(
        <div
          ref={enginePopupRef}
          className="fixed z-[9999]"
          style={{ bottom: enginePopupPos.bottom, left: enginePopupPos.left }}
        >
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.12 }}
            className="w-48 liquid-glass-popup rounded-xl overflow-hidden shadow-xl"
          >
            <div className="px-3 py-1.5 text-[10px] text-[var(--text-muted)] uppercase tracking-wider border-b border-[var(--border)]/50">
              Движок
            </div>
            {ENGINES.map((eng) => (
              <button
                key={eng.id}
                onClick={() => !eng.disabled && switchEngine(eng.id)}
                disabled={eng.disabled}
                className={`flex items-center gap-2 w-full px-3 py-2 text-left transition-colors ${
                  eng.disabled
                    ? 'opacity-40 cursor-not-allowed'
                    : currentEngine === eng.id ? 'bg-[var(--accent)]/10' : 'hover:bg-[var(--bg-hover)]'
                }`}
              >
                <eng.Icon size={14} className={currentEngine === eng.id ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'} />
                <span className={`text-xs font-medium ${
                  currentEngine === eng.id ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'
                }`}>{eng.label}</span>
                {eng.disabled && (
                  <span className="ml-auto text-[var(--text-muted)] text-[9px]">скоро</span>
                )}
                {!eng.disabled && currentEngine === eng.id && (
                  <span className="ml-auto text-[var(--accent)] text-[10px]">active</span>
                )}
              </button>
            ))}
          </motion.div>
        </div>,
        document.body
      )}
    </div>
  )
}
