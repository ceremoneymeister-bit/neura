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
}

const suggestions: Suggestion[] = [
  {
    icon: <PenLine size={16} />,
    title: 'Написать',
    desc: 'Письмо, статья, описание',
    prompt: 'Напиши текст: ',
  },
  {
    icon: <Lightbulb size={16} />,
    title: 'Идея',
    desc: 'Контент для соцсетей',
    prompt: 'Придумай идею для поста в Telegram-канал. Тема: ',
  },
  {
    icon: <BarChart3 size={16} />,
    title: 'Анализ',
    desc: 'Таблицы, отчёты, метрики',
    prompt: 'Проанализируй данные и подготовь краткий отчёт: ',
  },
  {
    icon: <CalendarCheck size={16} />,
    title: 'План',
    desc: 'Организуй задачи и приоритеты',
    prompt: 'Составь план на сегодня. Учти приоритеты и дедлайны.',
  },
  {
    icon: <FileText size={16} />,
    title: 'Документ',
    desc: 'PDF, презентация, отчёт',
    prompt: 'Создай документ: ',
  },
  {
    icon: <MessageSquare size={16} />,
    title: 'Штурм',
    desc: 'Идеи, варианты, решения',
    prompt: 'Давай проведём мозговой штурм по теме: ',
  },
]

export function SuggestionCards() {
  const handleClick = (s: Suggestion) => {
    document.dispatchEvent(
      new CustomEvent('neura:prefill-input', { detail: { text: s.prompt } })
    )
    setTimeout(() => {
      const textarea = document.querySelector<HTMLTextAreaElement>('textarea[data-chat-input]')
      if (textarea) {
        textarea.focus()
        textarea.setSelectionRange(s.prompt.length, s.prompt.length)
      }
    }, 50)
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.04, delayChildren: 0.05 } },
      }}
      className="flex flex-wrap justify-center gap-2 w-full max-w-2xl"
    >
      {suggestions.map((s) => (
        <motion.button
          key={s.title}
          variants={{
            hidden: { opacity: 0, y: 8 },
            visible: { opacity: 1, y: 0 },
          }}
          transition={{ duration: 0.15 }}
          onClick={() => handleClick(s)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-full text-[14px]
            liquid-glass-btn whitespace-nowrap"
        >
          <span className="text-[var(--text-muted)]">{s.icon}</span>
          <span className="text-[var(--text-primary)]">{s.title}</span>
        </motion.button>
      ))}
    </motion.div>
  )
}
