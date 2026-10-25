const API_URL = ((import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000').replace(/\/$/, '')
const TOKEN_KEY = 'pdi_token'

export const getToken = () => sessionStorage.getItem(TOKEN_KEY)
export const setToken = (t: string) => sessionStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => sessionStorage.removeItem(TOKEN_KEY)

export interface User {
  id: number
  name: string
  email: string
  role: string
  cargo_id: number | null
  department: string | null
  is_participant: boolean
  consented_at: string | null
}

export interface EvaluationMine {
  id: number
  evaluated_id: number
  evaluated_name: string
  type: 'auto' | 'gestor' | 'rh'
  status: 'pendente' | 'rascunho' | 'completo'
}

export interface CompetencyScore {
  code: string
  name: string
  description: string
  score: number | null
}

export interface DevelopmentInput {
  main_goal?: string
  needs?: string[]
  priority_competency?: string
  priority_reason?: string
  stay_in_role?: string
  future_role?: string | null
  dev_types?: string[]
  timeframe?: string
}

export interface EvaluationDetail extends EvaluationMine {
  submitted_at: string | null
  competencies: CompetencyScore[]
  development_input: DevelopmentInput | null
}

export interface ScoreItem {
  competency_code: string
  score: number
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

function errorMessage(body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'Dados inválidos. Revise os campos e tente novamente.'
  return 'Ocorreu um erro inesperado. Tente novamente.'
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers })
  } catch {
    throw new ApiError('Não foi possível conectar ao servidor.', 0)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && path !== '/auth/login') {
      clearToken()
      window.location.assign('/login')
    }
    throw new ApiError(errorMessage(body), res.status)
  }
  return body as T
}

export const login = (email: string, password: string) =>
  request<{ access_token: string; user: User }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

export const getMe = () => request<User>('/me')
export const consent = () => request<User>('/me/consent', { method: 'POST' })
export const listMine = () => request<EvaluationMine[]>('/evaluations/mine')
export const getEvaluation = (id: number) => request<EvaluationDetail>(`/evaluations/${id}`)

export const saveDraft = (id: number, scores: ScoreItem[], development_input: DevelopmentInput) =>
  request<EvaluationDetail>(`/evaluations/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ scores, development_input }),
  })

export const submitEvaluation = (id: number, scores: ScoreItem[], development_input: DevelopmentInput) =>
  request<EvaluationDetail>(`/evaluations/${id}/submit`, {
    method: 'POST',
    body: JSON.stringify({ scores, development_input }),
  })
