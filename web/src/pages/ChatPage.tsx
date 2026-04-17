import { useParams, useNavigate } from 'react-router-dom'
import { useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { Sun, Sunrise, Sunset, Moon } from 'lucide-react'
import { ChatView } from '@/components/chat'
import { ChatInput } from '@/components/chat/ChatInput'
import { SuggestionCards } from '@/components/chat/SuggestionCards'
import { useAuth } from '@/hooks/useAuth'
import { createConversation } from '@/api/conversations'
import { useToast } from '@/components/ui/Toast'

function getTimeGreeting(): string {
  const hour = new Date().getHours()
  if (hour >= 5 && hour < 12) return 'Доброе утро'
  if (hour >= 12 && hour < 17) return 'Добрый день'
  if (hour >= 17 && hour < 22) return 'Добрый вечер'
  return 'Доброй ночи'
}

function TimeIcon({ size = 28 }: { size?: number }) {
  const hour = new Date().getHours()
  const cls = "text-[var(--accent)]"
  if (hour >= 5 && hour < 10) return <Sunrise size={size} className={cls} strokeWidth={1.5} />
  if (hour >= 10 && hour < 17) return <Sun size={size} className={cls} strokeWidth={1.5} />
  if (hour >= 17 && hour < 21) return <Sunset size={size} className={cls} strokeWidth={1.5} />
  return <Moon size={size} className={cls} strokeWidth={1.5} />
}

export function ChatPage() {
  const { id } = useParams<{ id?: string }>()

  if (!id) {
    return <WelcomeScreen />
  }

  return <ChatView conversationId={id} />
}

function WelcomeScreen() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { error: showError } = useToast()
  const [sending, setSending] = useState(false)
  const firstName = user?.name?.split(' ')[0]

  const handleSend = useCallback(async (text: string, files: string[], model?: string, engine?: string) => {
    if (sending) return
    setSending(true)
    try {
      const conv = await createConversation()
      // Store pending message WITH engine and model for ChatView to pick up
      sessionStorage.setItem(
        `pending_msg_${conv.id}`,
        JSON.stringify({ text, files, model, engine: engine ?? 'claude' }),
      )
      // Save engine per-conversation
      if (engine) {
        sessionStorage.setItem(`engine_${conv.id}`, engine)
      }
      navigate(`/chat/${conv.id}`)
    } catch (e) {
      console.error('Failed to create conversation:', e)
      showError('Не удалось создать чат')
      setSending(false)
    }
  }, [sending, navigate])

  return (
    <div className="flex flex-col h-full">
      {/* Centered: greeting → input → suggestion cards */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 pb-[20vh]">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
          className="flex items-center gap-3 mb-8"
        >
          <TimeIcon size={32} />
          <h1
            className="text-3xl text-[var(--text-primary)]"
            style={{ fontFamily: 'var(--font-serif)', fontWeight: 400 }}
          >
            {firstName
              ? `${getTimeGreeting()}, ${firstName}`
              : getTimeGreeting()}
          </h1>
        </motion.div>

        {/* Input — centered */}
        <div className="w-full max-w-3xl">
          <ChatInput
            onSend={handleSend}
            disabled={sending}
            placeholder="Чем могу помочь сегодня?"
          />
        </div>

        {/* Suggestion cards — below input */}
        <div className="mt-4">
          <SuggestionCards />
        </div>
      </div>
    </div>
  )
}
