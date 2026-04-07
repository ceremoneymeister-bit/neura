import { useCallback, useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { Message } from '@/api/conversations'
import { getMessages, updateConversation, listConversations } from '@/api/conversations'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { WsChunk } from '@/hooks/useWebSocket'
import { MessageList } from './MessageList'
import { StreamingMessage } from './StreamingMessage'
import { ChatInput } from './ChatInput'
import { SuggestionCards } from './SuggestionCards'

interface ChatViewProps {
  conversationId: string
}

export function ChatView({ conversationId }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [statusText, setStatusText] = useState<string | null>(null)
  const [toolText, setToolText] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showScrollBottom, setShowScrollBottom] = useState(false)
  const [autoTitleDone, setAutoTitleDone] = useState(false)
  const [conversationModel, setConversationModel] = useState<string | undefined>(undefined)

  const scrollRef = useRef<HTMLDivElement>(null)
  const lastUserTextRef = useRef<string>('')
  const pendingSentRef = useRef(false)
  const queuedMessageRef = useRef<{ text: string; files: string[]; model?: string } | null>(null)
  const sendRef = useRef<(text: string, files: string[], model?: string) => void>(() => {})
  const convId = parseInt(conversationId, 10)

  // ── WebSocket message handler ─────────────────────────────────

  const handleMessage = useCallback((chunk: WsChunk) => {
    switch (chunk.type) {
      case 'status':
        setStatusText(chunk.content)
        setIsStreaming(true)
        break
      case 'text':
        setStreamingText(chunk.content)
        setStatusText(null)
        setIsStreaming(true)
        break
      case 'tool':
        setToolText(chunk.content)
        break
      case 'error':
        setError(chunk.content)
        setIsStreaming(false)
        setStreamingText('')
        setStatusText(null)
        setToolText(null)
        break
      case 'busy':
        setError(chunk.content)
        break
    }
  }, [])

  const handleDone = useCallback((final: WsChunk) => {
    const assistantMsg: Message = {
      id: Date.now(),
      role: 'assistant',
      content: final.content,
      files: [],
      model: final.model ?? null,
      duration_sec: final.duration ?? null,
      tokens_used: null,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, assistantMsg])
    setStreamingText('')
    setStatusText(null)
    setToolText(null)
    setIsStreaming(false)

    // Send queued message if any
    const queued = queuedMessageRef.current
    if (queued) {
      queuedMessageRef.current = null
      // Small delay to let state settle
      setTimeout(() => {
        sendRef.current(queued.text, queued.files, queued.model)
        setIsStreaming(true)
        lastUserTextRef.current = queued.text
      }, 100)
    }
  }, [])

  const { send, sendCancel, status: wsStatus } = useWebSocket({
    conversationId: isNaN(convId) ? null : convId,
    onMessage: handleMessage,
    onDone: handleDone,
  })

  // Keep ref in sync for queued message dispatch
  sendRef.current = send

  // ── Check for pending message from welcome screen ─────────────

  useEffect(() => {
    if (wsStatus !== 'connected' || pendingSentRef.current) return

    const key = `pending_msg_${convId}`
    const raw = sessionStorage.getItem(key)
    if (!raw) return

    sessionStorage.removeItem(key)
    pendingSentRef.current = true

    try {
      const { text, files } = JSON.parse(raw) as { text: string; files: string[] }
      if (!text && (!files || files.length === 0)) return

      // Add user message to UI
      const userMsg: Message = {
        id: Date.now(),
        role: 'user',
        content: text,
        files: files || [],
        model: null,
        duration_sec: null,
        tokens_used: null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
      lastUserTextRef.current = text

      // Auto-title
      if (!autoTitleDone) {
        setAutoTitleDone(true)
        const title = text.length > 60 ? text.slice(0, 60) + '\u2026' : text
        updateConversation(convId, { title }).catch(() => undefined)
        document.dispatchEvent(new CustomEvent('neura:set-chat-title', { detail: { title } }))
      }

      send(text, files || [])
    } catch {
      // ignore parse errors
    }
  }, [wsStatus, convId, send, autoTitleDone])

  // ── Load messages on conversationId change ────────────────────

  useEffect(() => {
    setMessages([])
    setStreamingText('')
    setStatusText(null)
    setToolText(null)
    setIsStreaming(false)
    setError(null)
    setAutoTitleDone(false)
    setShowScrollBottom(false)
    pendingSentRef.current = false

    if (isNaN(convId)) return

    setIsLoading(true)

    // Load conversation model preference
    listConversations()
      .then((convs) => {
        const conv = convs.find((c) => c.id === convId)
        if (conv?.model) setConversationModel(conv.model)
      })
      .catch(() => {})

    getMessages(convId)
      .then((msgs) => {
        setMessages(msgs)
        if (msgs.length > 0) {
          setAutoTitleDone(true)
          // Emit first user message as title for top bar
          const firstUser = msgs.find((m) => m.role === 'user')
          if (firstUser) {
            const t = firstUser.content.length > 60 ? firstUser.content.slice(0, 60) + '\u2026' : firstUser.content
            document.dispatchEvent(new CustomEvent('neura:set-chat-title', { detail: { title: t } }))
          }
        }
      })
      .catch(() => setError('Не удалось загрузить сообщения'))
      .finally(() => setIsLoading(false))
  }, [convId])

  // ── Auto-dismiss error after 8s ─────────────────────────────────

  useEffect(() => {
    if (!error) return
    const timer = setTimeout(() => setError(null), 8000)
    return () => clearTimeout(timer)
  }, [error])

  // ── Auto-scroll ────────────────────────────────────────────────

  const userScrolledUpRef = useRef(false)

  useEffect(() => {
    if (!userScrolledUpRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    if (isStreaming && !userScrolledUpRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [streamingText, isStreaming])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    userScrolledUpRef.current = distFromBottom > 120
    setShowScrollBottom(distFromBottom > 120)
  }

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
    userScrolledUpRef.current = false
    setShowScrollBottom(false)
  }

  // ── Send message ──────────────────────────────────────────────

  const handleSend = useCallback(async (text: string, files: string[], model?: string) => {
    // Queue message if currently streaming
    if (isStreaming) {
      queuedMessageRef.current = { text, files, model }
      // Still show user message in chat immediately
      const queuedMsg: Message = {
        id: Date.now(),
        role: 'user',
        content: text,
        files,
        model: null,
        duration_sec: null,
        tokens_used: null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, queuedMsg])
      return
    }

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: text,
      files,
      model: null,
      duration_sec: null,
      tokens_used: null,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setError(null)
    lastUserTextRef.current = text

    if (!autoTitleDone) {
      setAutoTitleDone(true)
      const title = text.length > 60 ? text.slice(0, 60) + '\u2026' : text
      updateConversation(convId, { title }).catch(() => undefined)
      document.dispatchEvent(new CustomEvent('neura:set-chat-title', { detail: { title } }))
    }

    setIsStreaming(true)
    setStatusText('Думаю...')
    send(text, files, model)
  }, [isStreaming, autoTitleDone, convId, send])

  // ── Regenerate last response ──────────────────────────────────

  const handleRegenerate = useCallback(() => {
    if (isStreaming || !lastUserTextRef.current) return

    setMessages((prev) => {
      const lastAssistantIdx = prev.reduceRight(
        (found, msg, idx) => (found === -1 && msg.role === 'assistant' ? idx : found),
        -1,
      )
      if (lastAssistantIdx === -1) return prev
      return prev.filter((_msg, i) => i !== lastAssistantIdx)
    })
    setError(null)
    send(lastUserTextRef.current, [])
  }, [isStreaming, send])

  // ── Stop streaming ────────────────────────────────────────────

  const handleStop = useCallback(() => {
    sendCancel()
    // Keep accumulated text as a partial message
    if (streamingText) {
      const partialMsg: Message = {
        id: Date.now(),
        role: 'assistant',
        content: streamingText + '\n\n*(остановлено)*',
        files: [],
        model: null,
        duration_sec: null,
        tokens_used: null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, partialMsg])
    }
    setIsStreaming(false)
    setStreamingText('')
    setStatusText(null)
    setToolText(null)
  }, [sendCancel, streamingText])

  // ── Render ────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full relative">
      {/* Messages scroll area */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
      >
        <div className="max-w-3xl mx-auto w-full">
          {/* Empty chat — show suggestions */}
          {messages.length === 0 && !isLoading && !isStreaming && (
            <div className="flex items-center justify-center py-16 px-4">
              <SuggestionCards />
            </div>
          )}

          <MessageList
            messages={messages}
            isLoading={isLoading}
            onRegenerate={handleRegenerate}
          />

          {isStreaming && (
            <StreamingMessage
              text={streamingText}
              statusText={statusText}
              toolText={toolText}
              onStop={handleStop}
            />
          )}

          <div className="h-2" />
        </div>
      </div>

      {/* Scroll-to-bottom FAB */}
      {showScrollBottom && (
        <button
          onClick={scrollToBottom}
          aria-label="Прокрутить вниз"
          title="Прокрутить вниз"
          className="absolute bottom-24 right-5 z-10 p-2 rounded-full bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--text-muted)] shadow-lg transition-all animate-fade-in"
        >
          <ChevronDown size={16} />
        </button>
      )}

      {/* Error banner */}
      {error && !isStreaming && (
        <div className="mx-4 mb-2 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between gap-4">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            aria-label="Закрыть ошибку"
            className="text-red-300 hover:text-red-100 text-xs underline shrink-0 transition-colors"
          >
            Закрыть
          </button>
        </div>
      )}

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        disabled={false}
        conversationId={conversationId}
        placeholder={isStreaming ? 'Агент отвечает... (Enter отправит после)' : 'Ответить...'}
        initialModel={conversationModel}
      />
    </div>
  )
}
