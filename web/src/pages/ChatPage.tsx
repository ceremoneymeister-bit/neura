import { useParams } from 'react-router-dom'
import { useCallback } from 'react'
import { motion } from 'framer-motion'
import { ChatView } from '@/components/chat'
import { useAuth } from '@/hooks/useAuth'

export function ChatPage() {
  const { id } = useParams<{ id?: string }>()

  if (!id) {
    return <WelcomeScreen />
  }

  return <ChatView conversationId={id} />
}

const EXAMPLES = [
  { icon: '\u{1F4DD}', title: '\u041D\u0430\u043F\u0438\u0441\u0430\u0442\u044C \u043F\u043E\u0441\u0442', desc: '\u041A\u043E\u043D\u0442\u0435\u043D\u0442 \u0434\u043B\u044F \u0441\u043E\u0446\u0441\u0435\u0442\u0435\u0439 \u0438\u043B\u0438 \u0431\u043B\u043E\u0433\u0430' },
  { icon: '\u{1F4CA}', title: '\u041F\u0440\u043E\u0430\u043D\u0430\u043B\u0438\u0437\u0438\u0440\u043E\u0432\u0430\u0442\u044C', desc: '\u0414\u0430\u043D\u043D\u044B\u0435, \u0442\u0435\u043A\u0441\u0442 \u0438\u043B\u0438 \u0441\u0442\u0440\u0430\u0442\u0435\u0433\u0438\u044E' },
  { icon: '\u{1F4A1}', title: '\u0413\u0435\u043D\u0435\u0440\u0438\u0440\u043E\u0432\u0430\u0442\u044C \u0438\u0434\u0435\u0438', desc: '\u0411\u0440\u0435\u0439\u043D\u0448\u0442\u043E\u0440\u043C \u043F\u043E \u043B\u044E\u0431\u043E\u0439 \u0442\u0435\u043C\u0435' },
  { icon: '\u{1F527}', title: '\u041D\u0430\u043F\u0438\u0441\u0430\u0442\u044C \u043A\u043E\u0434', desc: '\u0421\u043A\u0440\u0438\u043F\u0442\u044B, \u0444\u0443\u043D\u043A\u0446\u0438\u0438, \u043A\u043E\u043C\u043F\u043E\u043D\u0435\u043D\u0442\u044B' },
]

function WelcomeScreen() {
  const { user } = useAuth()
  const firstName = user?.name?.split(' ')[0]

  const handleCardClick = useCallback((text: string) => {
    document.dispatchEvent(
      new CustomEvent('neura:prefill-input', { detail: { text } })
    )
  }, [])

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 text-center px-4">
      {/* Animated N logo */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
        className="w-20 h-20 rounded-2xl flex items-center justify-center relative"
      >
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-[#7c3aed] via-[#a78bfa] to-[#7c3aed] opacity-20 animate-pulse" />
        <span className="text-3xl font-bold gradient-text relative z-10">N</span>
      </motion.div>

      {/* Greeting */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.1 }}
      >
        <h2 className="text-xl font-semibold text-[#f5f5f5]">
          {firstName ? `\u041F\u0440\u0438\u0432\u0435\u0442, ${firstName}` : '\u0414\u043E\u0431\u0440\u043E \u043F\u043E\u0436\u0430\u043B\u043E\u0432\u0430\u0442\u044C'}
        </h2>
        <p className="text-sm text-[#525252] mt-1.5">
          {'\u0427\u0435\u043C \u043C\u043E\u0433\u0443 \u043F\u043E\u043C\u043E\u0447\u044C?'}
        </p>
      </motion.div>

      {/* Example cards */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.2 }}
        className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full mt-1"
      >
        {EXAMPLES.map((ex, i) => (
          <motion.button
            key={ex.title}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.25 + i * 0.06 }}
            onClick={() => handleCardClick(`${ex.title}: ${ex.desc}`)}
            className="flex flex-col gap-2 p-4 rounded-[12px] bg-[#141414] border border-[#262626] hover:border-[#7c3aed]/50 hover:shadow-[0_0_20px_rgba(124,58,237,0.15)] transition-all text-left group cursor-pointer"
          >
            <span className="text-2xl">{ex.icon}</span>
            <p className="text-sm font-medium text-[#f5f5f5]">{ex.title}</p>
            <p className="text-xs text-[#525252] group-hover:text-[#a3a3a3] transition-colors leading-relaxed">
              {ex.desc}
            </p>
          </motion.button>
        ))}
      </motion.div>
    </div>
  )
}
