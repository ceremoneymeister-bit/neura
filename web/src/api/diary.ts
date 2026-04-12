import { api } from './client'

export interface DiaryEntry {
  id: number
  date: string
  time: string
  source: string
  user_message: string
  bot_response: string
  model: string | null
  duration_sec: number | null
  tools_used: string | null
  created_at: string
}

export async function getDiary(
  date?: string,
  limit = 50,
  offset = 0,
): Promise<DiaryEntry[]> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (date) params.set('date', date)
  return api.get<DiaryEntry[]>(`/api/diary?${params}`)
}

export async function searchDiary(q: string, limit = 20): Promise<DiaryEntry[]> {
  const params = new URLSearchParams({ q, limit: String(limit) })
  return api.get<DiaryEntry[]>(`/api/diary/search?${params}`)
}
