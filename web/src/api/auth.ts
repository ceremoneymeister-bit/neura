import { api } from './client'

export interface User {
  id: number
  email: string
  name: string
  capsule_id: string | null
  created_at: string | null
}

export interface AuthResponse {
  token: string
  user: User
}

export async function register(email: string, password: string, name: string): Promise<AuthResponse> {
  return api.post<AuthResponse>('/api/auth/register', { email, password, name })
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return api.post<AuthResponse>('/api/auth/login', { email, password })
}

export async function getMe(): Promise<{ user: User }> {
  return api.get<{ user: User }>('/api/auth/me')
}
