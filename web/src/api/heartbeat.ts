import { api } from './client'

export interface HeartbeatTask {
  name: string
  display_name?: string | null
  message: string
  schedule: string
  type: 'reminder' | 'task'
  enabled: boolean
}

export interface HeartbeatCreate {
  name: string
  display_name?: string
  message: string
  schedule?: string
  type?: 'reminder' | 'task'
  enabled?: boolean
}

export interface HeartbeatUpdate {
  name?: string
  display_name?: string | null
  message?: string
  schedule?: string
  type?: 'reminder' | 'task'
  enabled?: boolean
}

export async function listHeartbeats(): Promise<HeartbeatTask[]> {
  return api.get<HeartbeatTask[]>('/api/heartbeat')
}

export async function createHeartbeat(data: HeartbeatCreate): Promise<HeartbeatTask> {
  return api.post<HeartbeatTask>('/api/heartbeat', data)
}

export async function updateHeartbeat(taskName: string, data: HeartbeatUpdate): Promise<HeartbeatTask> {
  return api.patch<HeartbeatTask>(`/api/heartbeat/${encodeURIComponent(taskName)}`, data)
}

export async function deleteHeartbeat(taskName: string): Promise<void> {
  return api.delete<void>(`/api/heartbeat/${encodeURIComponent(taskName)}`)
}
