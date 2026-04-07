import { api } from './client'
import type { Conversation } from './conversations'

export interface Project {
  id: number
  name: string
  description: string
  instructions: string
  links: ProjectLink[]
  pinned: boolean
  icon: string
  sort_order: number
  chats_count: number
  created_at: string | null
}

export interface ProjectLink {
  url: string
  title?: string
  auto?: boolean
  found_at?: string | null
}

export interface ProjectMember {
  id: number
  capsule_id: string
  role: string
  added_at: string | null
}

export interface AutoContext {
  chats: {
    id: number
    title: string
    message_count: number
    last_user_message: string
    updated_at: string | null
  }[]
  auto_links: { url: string; found_at: string | null }[]
  total_messages: number
  total_chats: number
}

export async function listProjects(): Promise<Project[]> {
  return api.get<Project[]>('/api/projects')
}

export async function getProject(id: number): Promise<Project> {
  return api.get<Project>(`/api/projects/${id}`)
}

export async function createProject(
  name: string,
  icon = '',
  description = '',
  instructions = '',
): Promise<Project> {
  return api.post<Project>('/api/projects', { name, icon, description, instructions })
}

export async function updateProject(
  id: number,
  data: Partial<Pick<Project, 'name' | 'pinned' | 'icon' | 'description' | 'instructions' | 'links'>>,
): Promise<Project> {
  return api.patch<Project>(`/api/projects/${id}`, data)
}

export async function deleteProject(id: number): Promise<void> {
  return api.delete<void>(`/api/projects/${id}`)
}

export async function listProjectConversations(projectId: number): Promise<Conversation[]> {
  return api.get<Conversation[]>(`/api/projects/${projectId}/conversations`)
}

export async function getAutoContext(projectId: number): Promise<AutoContext> {
  return api.get<AutoContext>(`/api/projects/${projectId}/auto-context`)
}

export async function listProjectMembers(projectId: number): Promise<ProjectMember[]> {
  return api.get<ProjectMember[]>(`/api/projects/${projectId}/members`)
}

export async function addProjectMember(projectId: number, capsuleId: string, role = 'member'): Promise<ProjectMember> {
  return api.post<ProjectMember>(`/api/projects/${projectId}/members`, { capsule_id: capsuleId, role })
}

export async function removeProjectMember(projectId: number, memberId: number): Promise<void> {
  return api.delete<void>(`/api/projects/${projectId}/members/${memberId}`)
}
