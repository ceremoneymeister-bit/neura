/**
 * Base HTTP client — fetch wrapper with JWT auth, error handling, base URL.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function getToken(): string | null {
  return localStorage.getItem('neura_token')
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })

  if (res.status === 204) return undefined as T

  let data: unknown
  try {
    data = await res.json()
  } catch {
    data = null
  }

  if (!res.ok) {
    const detail = (data as { detail?: string })?.detail ?? res.statusText
    throw new ApiError(res.status, String(detail), data)
  }

  return data as T
}

export const api = {
  get:    <T>(path: string, signal?: AbortSignal) => request<T>('GET', path, undefined, signal),
  post:   <T>(path: string, body?: unknown)        => request<T>('POST', path, body),
  patch:  <T>(path: string, body?: unknown)        => request<T>('PATCH', path, body),
  delete: <T>(path: string)                        => request<T>('DELETE', path),
}

/**
 * Upload a file using multipart/form-data. Returns { path, filename, size }.
 */
export async function uploadFile(file: File): Promise<{ path: string; filename: string; size: number }> {
  const form = new FormData()
  form.append('file', file)

  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE_URL}/api/files/upload`, {
    method: 'POST',
    headers,
    body: form,
  })

  if (!res.ok) {
    const data = await res.json().catch(() => null)
    const detail = (data as { detail?: string })?.detail ?? res.statusText
    throw new ApiError(res.status, String(detail), data)
  }

  return res.json()
}

/**
 * Build a WebSocket URL with the current JWT token.
 * Uses VITE_WS_URL env var or derives from window.location.
 */
export function wsUrl(path: string): string {
  const token = getToken() ?? ''
  const base =
    import.meta.env.VITE_WS_URL ??
    `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  return `${base}${path}?token=${encodeURIComponent(token)}`
}
