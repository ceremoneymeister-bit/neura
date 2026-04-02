import { useCallback, useEffect, useRef, useState } from 'react'
import { wsUrl } from '@/api/client'

export type WsStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface WsChunk {
  type: 'status' | 'text' | 'tool' | 'done' | 'error'
  content: string
  model?: string
  duration?: number
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
  const MAX_RECONNECTS = 5

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('disconnected')
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
      try {
        const chunk = JSON.parse(evt.data) as WsChunk
        if (chunk.type === 'done') {
          onDone?.(chunk)
        }
        onMessage(chunk)
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = () => {
      setStatus('error')
    }

    ws.onclose = (evt) => {
      wsRef.current = null
      if (evt.code === 4001) {
        // Auth error — don't reconnect
        setStatus('error')
        return
      }
      setStatus('disconnected')
      if (reconnectCount.current < MAX_RECONNECTS) {
        const delay = Math.min(1000 * 2 ** reconnectCount.current, 10000)
        reconnectCount.current++
        reconnectTimer.current = setTimeout(connect, delay)
      }
    }
  }, [conversationId, disconnect, onMessage, onDone])

  useEffect(() => {
    if (conversationId) {
      reconnectCount.current = 0
      connect()
    } else {
      disconnect()
    }
    return () => disconnect()
  }, [conversationId, connect, disconnect])

  const send = useCallback((text: string, files: string[] = []) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ text, files }))
    }
  }, [])

  return { status, send, connect, disconnect }
}
