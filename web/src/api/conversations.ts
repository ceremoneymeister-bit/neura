import { api } from './client'

export interface Conversation {
  id: number
  title: string
  project_id: number | null
  pinned: boolean
  last_message: string | null
  created_at: string | null
  updated_at: string | null
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  files: string[]
  model: string | null
  duration_sec: number | null
  tokens_used: number | null
  created_at: string | null
}

export interface ConversationListParams {
  project_id?: number
}

export async function listConversations(_params?: ConversationListParams): Promise<Conversation[]> {
  return api.get<Conversation[]>('/api/conversations')
}

export async function createConversation(
  title?: string,
  project_id?: number,
): Promise<Conversation> {
  return api.post<Conversation>('/api/conversations', { title, project_id })
}

export async function updateConversation(
  id: number,
  data: Partial<Pick<Conversation, 'title' | 'project_id' | 'pinned'>>,
): Promise<Conversation> {
  return api.patch<Conversation>(`/api/conversations/${id}`, data)
}

export async function deleteConversation(id: number): Promise<void> {
  return api.delete<void>(`/api/conversations/${id}`)
}

export async function getMessages(conversationId: number): Promise<Message[]> {
  return api.get<Message[]>(`/api/conversations/${conversationId}/messages`)
}
