import { motion } from 'framer-motion'
import {
  CalendarCheck,
  Lightbulb,
  BarChart3,
  PenLine,
  FileText,
  MessageSquare,
} from 'lucide-react'

interface Suggestion {
  icon: React.ReactNode
  title: string
  desc: string
  prompt: string
  skill?: string
}

const suggestions: Suggestion[] = [
  {
    icon: <CalendarCheck size={18} />,
    title: 'Составь план',
    desc: 'Организуй задачи и приоритеты',
    prompt: 'Составь план на сегодня. Учти приоритеты и дедлайны.',
    skill: 'writing-plans',
  },
  {
    icon: <Lightbulb size={18} />,
    title: 'Придумай идею',
    desc: 'Контент для соцсетей',
    prompt: 'Придумай идею для поста в Telegram-канал. Тема: ',
    skill: 'social-content',
  },
  {
    icon: <BarChart3 size={18} />,
    title: 'Анализ данных',
    desc: 'Таблицы, отчёты, метрики',
    prompt: 'Проанализируй данные и подготовь краткий отчёт: ',
    skill: 'brainstorming',
  },
  {
    icon: <PenLine size={18} />,
    title: 'Напиши текст',
    desc: 'Письмо, статья, описание',
    prompt: 'Напиши текст: ',
    skill: 'copywriting',
  },
  {
    icon: <FileText size={18} />,
    title: 'Создай документ',
    desc: 'PDF, презентация, отчёт',
    prompt: 'Создай документ: ',
    skill: 'notion-pdf',
  },
  {
    icon: <MessageSquare size={18} />,
    title: 'Мозговой штурм',
    desc: 'Идеи, варианты, решения',
    prompt: 'Давай проведём мозговой штурм по теме: ',
    skill: 'brainstorming',
  },
]

interface SuggestionCardsProps {
  columns?: 2 | 3
}

export function SuggestionCards({ columns = 2 }: SuggestionCardsProps) {
  const handleClick = (s: Suggestion) => {
    // Dispatch prefill event — ChatInput picks it up
    document.dispatchEvent(
      new CustomEvent('neura:prefill-input', { detail: { text: s.prompt } })
    )
    // Focus the input
    setTimeout(() => {
      const textarea = document.querySelector<HTMLTextAreaElement>('textarea[data-chat-input]')
      if (textarea) {
        textarea.focus()
        // Place cursor at the end
        textarea.setSelectionRange(s.prompt.length, s.prompt.length)
      }
    }, 50)
  }

  const gridClass = columns === 3
    ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3'
    : 'grid grid-cols-1 sm:grid-cols-2 gap-3'

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
      }}
      className={`${gridClass} w-full max-w-4xl`}
    >
      {suggestions.map((s) => (
        <motion.button
          key={s.title}
          variants={{
            hidden: { opacity: 0, y: 10 },
            visible: { opacity: 1, y: 0 },
          }}
          transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          onClick={() => handleClick(s)}
          className="flex items-start gap-3 px-4 py-3.5 rounded-xl text-left
            bg-[var(--bg-card)] border border-[var(--border)]
            hover:border-[var(--accent)]/30 hover:bg-[var(--bg-hover)]
            transition-colors duration-150 group"
        >
          <span className="text-[var(--accent)] mt-0.5 shrink-0">{s.icon}</span>
          <div className="min-w-0 flex-1">
            <span className="block text-sm text-[var(--text-primary)]">{s.title}</span>
            <span className="block text-xs text-[var(--text-muted)] mt-0.5">{s.desc}</span>
            {s.skill && (
              <span className="inline-block mt-1.5 px-1.5 py-0.5 rounded text-[9px] font-medium bg-[var(--accent-muted)] text-[var(--accent)] opacity-0 group-hover:opacity-100 transition-opacity">
                {s.skill}
              </span>
            )}
          </div>
        </motion.button>
      ))}
    </motion.div>
  )
}
