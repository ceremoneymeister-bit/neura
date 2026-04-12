import { api } from './client'

export interface SearchResult {
  message_id: number
  conversation_id: number
  conversation_title: string | null
  role: string
  preview: string
  created_at: string
}

export async function searchMessages(q: string, limit = 20): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q, limit: String(limit) })
  return api.get<SearchResult[]>(`/api/search?${params}`)
}
