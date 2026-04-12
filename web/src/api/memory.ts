import { api } from './client'

export interface MemoryEntry {
  id: number
  content: string
  source: string | null
  score: number | null
  created_at: string
}

export interface LearningEntry {
  id: number
  content: string
  type: string
  source: string | null
  created_at: string
}

export async function getMemory(limit = 50, offset = 0): Promise<MemoryEntry[]> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return api.get<MemoryEntry[]>(`/api/memory?${params}`)
}

export async function deleteMemory(id: number): Promise<void> {
  return api.delete<void>(`/api/memory/${id}`)
}

export async function getLearnings(limit = 50): Promise<LearningEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  return api.get<LearningEntry[]>(`/api/learnings?${params}`)
}
