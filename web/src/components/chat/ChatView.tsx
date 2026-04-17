import { useCallback, useEffect, useRef, useState } from 'react'
import { ChevronDown, Download } from 'lucide-react'
import type { Message } from '@/api/conversations'
import { getMessages, updateConversation, listConversations } from '@/api/conversations'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { WsChunk, ToolStep } from '@/hooks/useWebSocket'
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
  const [toolSteps, setToolSteps] = useState<ToolStep[]>([])
  const [conversationModel, setConversationModel] = useState<string | undefined>(undefined)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const PAGE_SIZE = 50

  const scrollRef = useRef<HTMLDivElement>(null)
  const lastUserTextRef = useRef<string>('')
  const pendingSentRef = useRef(false)
  const queuedMessageRef = useRef<{ text: string; files: string[]; model?: string } | null>(null)
  const sendRef = useRef<(text: string, files: string[], model?: string) => void>(() => {})
  const convId = parseInt(conversationId, 10)
  const convIdRef = useRef(convId)
  convIdRef.current = convId

  // ── WebSocket message handler ─────────────────────────────────

  const handleMessage = useCallback((chunk: WsChunk) => {
    // Ignore chunks arriving after user switched to a different conversation
    if (convIdRef.current !== convId) return
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
      case 'tool_start':
        setToolText(chunk.content)
        setIsStreaming(true)
        setToolSteps((prev) => [
          ...prev,
          {
            tool_id: chunk.tool_id ?? `t_${Date.now()}`,
            tool: chunk.tool ?? 'unknown',
            label: chunk.content,
            detail: chunk.detail,
            status: 'running',
            startedAt: Date.now(),
          },
        ])
        break
      case 'tool_end':
        setToolSteps((prev) =>
          prev.map((s) =>
            s.tool_id === chunk.tool_id ? { ...s, status: 'done' as const } : s,
          ),
        )
        setToolText(null)
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
  }, [convId])

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
    setToolSteps([])

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
      const { text, files, model, engine } = JSON.parse(raw) as { text: string; files: string[]; model?: string; engine?: string }
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

      send(text, files || [], model, engine)
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
    setHasMore(false)
    setLoadingMore(false)
    pendingSentRef.current = false

    if (isNaN(convId)) return

    setConversationModel(undefined)  // reset before async load to avoid stale model
    setIsLoading(true)

    // Load conversation model preference
    listConversations()
      .then((convs) => {
        const conv = convs.find((c) => c.id === convId)
        if (conv?.model) setConversationModel(conv.model)
      })
      .catch(() => {})

    getMessages(convId, PAGE_SIZE)
      .then((msgs) => {
        setMessages(msgs)
        setHasMore(msgs.length >= PAGE_SIZE)
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

  // ── Clear streaming state on disconnect ─────────────────────────

  useEffect(() => {
    if ((wsStatus === 'disconnected' || wsStatus === 'error') && isStreaming) {
      // Save partial text as a message if any
      if (streamingText) {
        const partialMsg: Message = {
          id: Date.now(),
          role: 'assistant',
          content: streamingText + '\n\n*(соединение потеряно)*',
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
      if (wsStatus === 'disconnected') {
        setError('Соединение потеряно. Переподключаюсь...')
      } else {
        setError('Ошибка соединения. Обновите страницу.')
      }
    }
  }, [wsStatus]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auto-dismiss error after 8s ─────────────────────────────────

  useEffect(() => {
    if (!error) return
    const timer = setTimeout(() => setError(null), 8000)
    return () => clearTimeout(timer)
  }, [error])

  // ── Load more (older messages) ──────────────────────────────────

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore || isNaN(convId)) return
    setLoadingMore(true)
    const el = scrollRef.current
    const prevScrollHeight = el?.scrollHeight ?? 0
    try {
      const older = await getMessages(convId, PAGE_SIZE, messages.length)
      if (older.length < PAGE_SIZE) setHasMore(false)
      if (older.length > 0) {
        setMessages((prev) => [...older, ...prev])
        // Preserve scroll position after prepending
        requestAnimationFrame(() => {
          if (el) {
            el.scrollTop = el.scrollHeight - prevScrollHeight
          }
        })
      }
    } catch {
      setError('Не удалось загрузить сообщения')
    } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, hasMore, convId, messages.length])

  // ── Auto-scroll ────────────────────────────────────────────────

  const userScrolledUpRef = useRef(false)
  const isStreamingRef = useRef(false)
  isStreamingRef.current = isStreaming

  const doScroll = useCallback(() => {
    requestAnimationFrame(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight
      }
    })
  }, [])

  useEffect(() => {
    if (!userScrolledUpRef.current && scrollRef.current) {
      doScroll()
    }
  }, [messages, doScroll])

  useEffect(() => {
    if (isStreaming && !userScrolledUpRef.current && scrollRef.current) {
      doScroll()
    }
  }, [streamingText, isStreaming, doScroll])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    // During streaming, don't mark as "scrolled up" from layout jumps
    if (isStreamingRef.current && distFromBottom < 150) return
    userScrolledUpRef.current = distFromBottom > 50
    setShowScrollBottom(distFromBottom > 50)
  }

  const scrollToBottom = () => {
    userScrolledUpRef.current = false
    setShowScrollBottom(false)
    doScroll()
  }

  // ── Send message ──────────────────────────────────────────────

  const handleSend = useCallback(async (text: string, files: string[], model?: string, engine?: string) => {
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

    const sent = send(text, files, model, engine)
    if (sent) {
      setIsStreaming(true)
      setStatusText('Думаю...')
    } else {
      setError('Нет соединения. Переподключаюсь...')
    }
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

  // ── Export conversation ────────────────────────────────────────

  const handleExport = useCallback(() => {
    if (messages.length === 0) return
    const lines = messages.map((m) => {
      const role = m.role === 'user' ? '\u{1F464} \u0412\u044B' : '\u{1F916} \u041D\u044D\u0439\u0440\u0430'
      const time = m.created_at ? new Date(m.created_at).toLocaleString('ru-RU') : ''
      return `### ${role}${time ? ` (${time})` : ''}\n\n${m.content}\n`
    })
    const md = `# \u0414\u0438\u0430\u043B\u043E\u0433\n\n\u042D\u043A\u0441\u043F\u043E\u0440\u0442\u0438\u0440\u043E\u0432\u0430\u043D\u043E: ${new Date().toLocaleString('ru-RU')}\n\n---\n\n${lines.join('\n---\n\n')}`
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `chat-${conversationId}-${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [messages, conversationId])

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
          {/* Load more button */}
          {hasMore && (
            <div className="flex justify-center py-3">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="text-xs text-[var(--accent)] hover:text-[var(--accent-light)] transition-colors px-4 py-2 rounded-lg liquid-glass-btn disabled:opacity-50"
              >
                {loadingMore ? 'Загрузка...' : 'Загрузить ранние сообщения'}
              </button>
            </div>
          )}

          {/* Export button */}
          {messages.length > 0 && (
            <div className="flex justify-end px-4 pt-2">
              <button
                onClick={handleExport}
                title="\u042D\u043A\u0441\u043F\u043E\u0440\u0442 \u0434\u0438\u0430\u043B\u043E\u0433\u0430"
                className="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors px-3 py-1.5 rounded-lg hover:bg-[var(--bg-hover)] flex items-center gap-1.5"
              >
                <Download size={12} />
                Экспорт
              </button>
            </div>
          )}

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
              toolSteps={toolSteps}
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
          className="absolute bottom-24 right-5 z-10 w-9 h-9 flex items-center justify-center rounded-full liquid-glass text-[var(--text-secondary)] hover:text-[var(--text-primary)] shadow-lg transition-all animate-fade-in"
        >
          <ChevronDown size={16} />
        </button>
      )}

      {/* Error banner */}
      {error && !isStreaming && (
        <div className="mx-4 mb-2 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between gap-4">
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
