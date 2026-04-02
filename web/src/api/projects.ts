import { api } from './client'

export interface Project {
  id: number
  name: string
  pinned: boolean
  icon: string
  sort_order: number
  chats_count: number
  created_at: string | null
}

export async function listProjects(): Promise<Project[]> {
  return api.get<Project[]>('/api/projects')
}

export async function createProject(name: string, icon = '📁'): Promise<Project> {
  return api.post<Project>('/api/projects', { name, icon })
}

export async function updateProject(
  id: number,
  data: Partial<Pick<Project, 'name' | 'pinned' | 'icon'>>,
): Promise<Project> {
  return api.patch<Project>(`/api/projects/${id}`, data)
}

export async function deleteProject(id: number): Promise<void> {
  return api.delete<void>(`/api/projects/${id}`)
}
