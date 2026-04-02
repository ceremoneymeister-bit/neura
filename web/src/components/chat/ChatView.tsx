import { useCallback, useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { Message } from '@/api/conversations'
import { getMessages, updateConversation } from '@/api/conversations'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { WsChunk } from '@/hooks/useWebSocket'
import { MessageList } from './MessageList'
import { StreamingMessage } from './StreamingMessage'
import { ChatInput } from './ChatInput'

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

  const scrollRef = useRef<HTMLDivElement>(null)
  const lastUserTextRef = useRef<string>('')
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
  }, [])

  const { send } = useWebSocket({
    conversationId: isNaN(convId) ? null : convId,
    onMessage: handleMessage,
    onDone: handleDone,
  })

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

    if (isNaN(convId)) return

    setIsLoading(true)
    getMessages(convId)
      .then((msgs) => {
        setMessages(msgs)
        // If there are existing messages, mark auto-title as done
        if (msgs.length > 0) setAutoTitleDone(true)
      })
      .catch(() => setError('Не удалось загрузить сообщения'))
      .finally(() => setIsLoading(false))
  }, [convId])

  // ── Auto-scroll ────────────────────────────────────────────────

  useEffect(() => {
    if (!showScrollBottom && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, showScrollBottom])

  useEffect(() => {
    if (isStreaming && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [streamingText, isStreaming])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    setShowScrollBottom(distFromBottom > 120)
  }

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
    setShowScrollBottom(false)
  }

  // ── Send message ──────────────────────────────────────────────

  const handleSend = useCallback(async (text: string, files: string[]) => {
    if (isStreaming) return

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

    // Auto-title: set conversation title from first user message
    if (!autoTitleDone) {
      setAutoTitleDone(true)
      const title = text.length > 60 ? text.slice(0, 60) + '…' : text
      updateConversation(convId, { title }).catch(() => undefined)
    }

    send(text, files)
  }, [isStreaming, autoTitleDone, convId, send])

  // ── Regenerate last response ──────────────────────────────────

  const handleRegenerate = useCallback(() => {
    if (isStreaming || !lastUserTextRef.current) return

    setMessages((prev) => {
      // Remove the last assistant message
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
    setIsStreaming(false)
    setStreamingText('')
    setStatusText(null)
    setToolText(null)
  }, [])

  // ── Render ────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full relative">
      {/* Messages scroll area */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
      >
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

        {/* Bottom anchor for scroll */}
        <div className="h-2" />
      </div>

      {/* Scroll-to-bottom FAB */}
      {showScrollBottom && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-24 right-5 z-10 p-2 rounded-full bg-[#141414] border border-[#262626] text-[#a3a3a3] hover:text-[#f5f5f5] hover:border-[#525252] shadow-lg transition-all animate-fade-in"
        >
          <ChevronDown size={16} />
        </button>
      )}

      {/* Error banner */}
      {error && !isStreaming && (
        <div className="mx-4 mb-2 px-4 py-2.5 rounded-[8px] bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between gap-4">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-300 hover:text-red-100 text-xs underline shrink-0 transition-colors"
          >
            Закрыть
          </button>
        </div>
      )}

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        disabled={isStreaming}
        conversationId={conversationId}
      />
    </div>
  )
}
