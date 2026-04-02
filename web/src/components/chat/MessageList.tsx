import type { Message } from '@/api/conversations'
import { MessageBubble } from './MessageBubble'

interface MessageListProps {
  messages: Message[]
  isLoading?: boolean
  onRegenerate?: () => void
}

export function MessageList({ messages, isLoading = false, onRegenerate }: MessageListProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 py-4">
        {[0, 1, 2].map((i) => (
          <MessageSkeleton key={i} isUser={i % 2 === 0} />
        ))}
      </div>
    )
  }

  if (messages.length === 0) {
    return null
  }

  // Index of the last assistant message (for regenerate button)
  const lastAssistantIdx = messages.reduceRight(
    (found, msg, idx) => (found === -1 && msg.role === 'assistant' ? idx : found),
    -1,
  )

  return (
    <div className="pb-4">
      {messages.map((msg, idx) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          isLast={idx === lastAssistantIdx}
          onRegenerate={idx === lastAssistantIdx && onRegenerate ? onRegenerate : undefined}
        />
      ))}
    </div>
  )
}

function MessageSkeleton({ isUser }: { isUser: boolean }) {
  return (
    <div className={`flex gap-3 px-4 py-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className="skeleton w-7 h-7 rounded-full shrink-0" />
      <div className={`flex flex-col gap-1.5 ${isUser ? 'items-end' : ''}`} style={{ width: 280 }}>
        <div className="skeleton h-3.5 rounded w-3/4" />
        <div className="skeleton h-3.5 rounded w-full" />
        <div className="skeleton h-3.5 rounded w-1/2" />
      </div>
    </div>
  )
}
