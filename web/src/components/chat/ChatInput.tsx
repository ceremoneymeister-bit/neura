import {
  useRef,
  useState,
  useEffect,
  useCallback,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from 'react'
import { Paperclip, Mic, MicOff, Send, X } from 'lucide-react'
import { uploadFile } from '@/api/client'

interface AttachedFile {
  name: string
  path: string
}

interface ChatInputProps {
  onSend: (text: string, files: string[]) => void
  disabled?: boolean
  conversationId?: string
}

export function ChatInput({ onSend, disabled = false, conversationId }: ChatInputProps) {
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [isRecording, setIsRecording] = useState(false)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<BlobPart[]>([])

  // Restore draft from sessionStorage on conversation change
  useEffect(() => {
    const draft = conversationId
      ? (sessionStorage.getItem(`draft_${conversationId}`) ?? '')
      : ''
    setText(draft)
  }, [conversationId])

  // Save draft to sessionStorage
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
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`
  }, [text])

  // Focus when conversation changes
  useEffect(() => {
    if (!disabled) textareaRef.current?.focus()
  }, [conversationId, disabled])

  const doSend = useCallback(() => {
    const trimmed = text.trim()
    if ((!trimmed && attachedFiles.length === 0) || disabled || isUploading) return

    onSend(trimmed, attachedFiles.map((f) => f.path))
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

  const uploadFiles = useCallback(async (selected: File[]) => {
    if (selected.length === 0) return
    setIsUploading(true)
    try {
      const results = await Promise.all(selected.map(uploadFile))
      setAttachedFiles((prev) => [
        ...prev,
        ...results.map((r) => ({ name: r.filename, path: r.path })),
      ])
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setIsUploading(false)
    }
  }, [])

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? [])
    e.target.value = ''
    await uploadFiles(selected)
  }

  const removeFile = (idx: number) => {
    setAttachedFiles((prev) => prev.filter((_f, i) => i !== idx))
  }

  // Drag & drop on the whole input container
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
    }
  }

  const canSend = (text.trim().length > 0 || attachedFiles.length > 0) && !disabled && !isUploading

  return (
    <div
      className="relative px-4 pb-4 pt-2 shrink-0"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none rounded-[12px] mx-4">
          <div className="border-2 border-dashed border-[#7c3aed] rounded-[12px] px-8 py-4 bg-[#7c3aed]/10 text-[#7c3aed] text-sm font-medium">
            Перетащите файлы сюда
          </div>
        </div>
      )}

      {/* File chips */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {attachedFiles.map((f, i) => (
            <div
              key={i}
              className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-[6px] bg-[#1e1e1e] border border-[#262626] text-[#a3a3a3]"
            >
              <span>📎</span>
              <span className="max-w-[140px] truncate">{f.name}</span>
              <button
                onClick={() => removeFile(i)}
                className="text-[#525252] hover:text-[#f5f5f5] transition-colors ml-0.5 flex-shrink-0"
                title="Удалить"
              >
                <X size={11} />
              </button>
            </div>
          ))}
          {isUploading && (
            <div className="flex items-center gap-1 text-xs px-2 py-1 rounded-[6px] bg-[#1e1e1e] border border-[#262626] text-[#525252]">
              <span className="animate-pulse">⏳</span>
              <span>Загрузка...</span>
            </div>
          )}
        </div>
      )}

      {/* Input box */}
      <div
        className={`flex items-end gap-2 bg-[#141414] border rounded-[12px] px-3 py-2 transition-colors ${
          isDragging
            ? 'border-[#7c3aed]'
            : 'border-[#262626] focus-within:border-[#7c3aed]/50'
        }`}
      >
        {/* Attach */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          title="Прикрепить файл"
          className="shrink-0 p-1.5 text-[#525252] hover:text-[#a3a3a3] transition-colors disabled:opacity-30"
        >
          <Paperclip size={16} />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Напишите сообщение..."
          rows={1}
          className="flex-1 bg-transparent text-sm text-[#f5f5f5] placeholder-[#525252] resize-none outline-none leading-6 py-0.5 min-h-[24px] max-h-[240px]"
        />

        {/* Voice */}
        <button
          type="button"
          onClick={toggleRecording}
          disabled={disabled}
          title={isRecording ? 'Остановить запись' : 'Голосовое сообщение'}
          className={`shrink-0 p-1.5 transition-colors disabled:opacity-30 ${
            isRecording
              ? 'text-red-400 pulse-ring rounded-full'
              : 'text-[#525252] hover:text-[#a3a3a3]'
          }`}
        >
          {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
        </button>

        {/* Send */}
        <button
          type="button"
          onClick={doSend}
          disabled={!canSend}
          title="Отправить (Enter)"
          className="shrink-0 p-1.5 rounded-[8px] bg-[#7c3aed] text-white hover:bg-[#6d28d9] active:bg-[#5b21b6] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <Send size={15} />
        </button>
      </div>

      <p className="text-center text-[10px] text-[#3a3a3a] mt-1.5 select-none">
        Enter — отправить · Shift+Enter — новая строка
      </p>
    </div>
  )
}
