import { useCallback, useEffect, useRef, useState } from 'react'
import { wsUrl } from '@/api/client'

export type WsStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface ToolStep {
  tool_id: string
  tool: string       // "Read", "Edit", "Bash", etc.
  label: string      // "📖 Читаю · core/engine.py"
  detail?: {
    file?: string
    command?: string
    pattern?: string
    query?: string
    path?: string
  }
  status: 'running' | 'done'
  startedAt: number  // Date.now()
}

export interface WsChunk {
  type: 'status' | 'text' | 'tool' | 'tool_start' | 'tool_end' | 'done' | 'error' | 'busy' | 'ping'
  content: string
  model?: string
  duration?: number
  active_chats?: number[]
  tool?: string
  tool_id?: string
  detail?: ToolStep['detail']
}

interface UseWebSocketOptions {
  conversationId: number | null
  onMessage: (chunk: WsChunk) => void
  onDone?: (final: WsChunk) => void
}

export function useWebSocket({ conversationId, onMessage, onDone }: UseWebSocketOptions) {
  const [status, setStatus] = useState<WsStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectCount = useRef(0)
  const lastMessageTime = useRef<number>(0)
  const staleTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const MAX_RECONNECTS = 8

  const clearStaleTimer = () => {
    if (staleTimer.current) {
      clearTimeout(staleTimer.current)
      staleTimer.current = null
    }
  }

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
    clearStaleTimer()
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('disconnected')
  }, [])

  const scheduleReconnect = useCallback((connectFn: () => void) => {
    if (reconnectCount.current < MAX_RECONNECTS) {
      const delay = Math.min(1000 * 2 ** reconnectCount.current, 15000)
      reconnectCount.current++
      setStatus('disconnected')
      reconnectTimer.current = setTimeout(connectFn, delay)
    } else {
      setStatus('error')
    }
  }, [])

  const connect = useCallback(() => {
    if (!conversationId) return
    disconnect()

    setStatus('connecting')
    const url = wsUrl(`/ws/chat/${conversationId}`)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      reconnectCount.current = 0
    }

    ws.onmessage = (evt: MessageEvent<string>) => {
      lastMessageTime.current = Date.now()
      try {
        const chunk = JSON.parse(evt.data) as WsChunk
        // Heartbeat: respond to server ping with pong
        if (chunk.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }))
          return
        }
        if (chunk.type === 'done') {
          clearStaleTimer()
          onDone?.(chunk)
        }
        onMessage(chunk)
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = () => {
      // Don't set 'error' immediately — let onclose handle reconnect
      // onerror is always followed by onclose
    }

    ws.onclose = (evt) => {
      wsRef.current = null
      clearStaleTimer()
      if (evt.code === 4001) {
        // Auth error — don't reconnect
        setStatus('error')
        return
      }
      scheduleReconnect(connect)
    }
  }, [conversationId, disconnect, onMessage, onDone, scheduleReconnect])

  useEffect(() => {
    if (conversationId) {
      reconnectCount.current = 0
      connect()
    } else {
      disconnect()
    }
    return () => disconnect()
  }, [conversationId, connect, disconnect])

  const send = useCallback((text: string, files: string[] = [], model?: string, engine?: string): boolean => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ text, files, ...(model && { model }), ...(engine && { engine }) }))
      // Start stale connection detection — if no message in 45s, emit error
      lastMessageTime.current = Date.now()
      clearStaleTimer()
      staleTimer.current = setTimeout(() => {
        if (Date.now() - lastMessageTime.current >= 44000) {
          onMessage({ type: 'error', content: 'Нет ответа от сервера. Попробуйте отправить снова.' })
        }
      }, 45000)
      return true
    }
    // Socket not open — notify caller
    return false
  }, [onMessage])

  const sendCancel = useCallback(() => {
    clearStaleTimer()
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel' }))
    }
  }, [])

  return { status, send, sendCancel, connect, disconnect }
}
