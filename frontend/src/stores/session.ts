import { create } from 'zustand'
import type {
  ConversionProgress,
  ConversionSettings,
  PipelineEvent,
  PipelineStageKey,
  User,
} from '@/types'

type Step = 'upload' | 'progress' | 'editor' | 'history'

interface SessionState {
  // Auth
  user: User | null
  token: string | null

  // Session
  step: Step
  file: File | null
  runId: string | null           // was sessionId — now points to orchestrator run
  progress: ConversionProgress | null
  yaml: string | null
  error: string | null
  settings: ConversionSettings
  thinking: string
  events: PipelineEvent[]        // audit trail from Redis Stream
  currentStage: PipelineStageKey | null  // 6-stage granular tracking

  // Auth actions
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void

  // Session actions
  setFile: (file: File) => void
  setRunId: (id: string) => void
  setStep: (step: Step) => void
  loadHistoryYaml: (yaml: string) => void
  updateProgress: (progress: ConversionProgress) => void
  setCurrentStage: (stage: PipelineStageKey) => void
  appendEvent: (event: PipelineEvent) => void
  clearEvents: () => void
  setYaml: (yaml: string) => void
  setError: (error: string | null) => void
  setSettings: (settings: ConversionSettings) => void
  appendThinking: (text: string) => void
  clearThinking: () => void
  reset: () => void
}

const AUTH_API = 'http://localhost:8080'

export const useSessionStore = create<SessionState>((set) => ({
  // Auth state
  user: null,
  token: null,

  // Session state
  step: 'upload',
  file: null,
  runId: null,
  progress: null,
  yaml: null,
  error: null,
  settings: { script_type: 'tv', language: 'zh' },
  thinking: '',
  events: [],
  currentStage: null,

  // Auth actions — real API calls to auth-service
  login: async (username, password) => {
    const res = await fetch(`${AUTH_API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const json = await res.json()
    if (json.code !== 200) {
      throw new Error(json.message || '登录失败')
    }
    const { token, userInfo } = json.data
    set({
      token,
      user: {
        id: userInfo.userId,
        username: userInfo.username,
        email: userInfo.email,
      },
    })
  },
  register: async (username, email, password) => {
    const res = await fetch(`${AUTH_API}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    })
    const json = await res.json()
    if (json.code !== 200) {
      throw new Error(json.message || '注册失败')
    }
  },
  logout: () => {
    // Call backend logout (fire-and-forget)
    fetch(`${AUTH_API}/api/auth/logout`, { method: 'POST' }).catch(() => {})
    set({
      user: null,
      token: null,
      step: 'upload',
      file: null,
      runId: null,
      progress: null,
      yaml: null,
      error: null,
      thinking: '',
      events: [],
      currentStage: null,
    })
  },

  // Session actions
  setFile: (file) => set({ file }),
  setRunId: (id) => set({ runId: id }),
  setStep: (step) => set({ step }),
  loadHistoryYaml: (yaml) => set({ yaml, step: 'editor' }),
  updateProgress: (progress) => set({ progress }),
  setCurrentStage: (stage) => set({ currentStage: stage }),
  appendEvent: (event) => set((s) => ({ events: [...s.events, event] })),
  clearEvents: () => set({ events: [] }),
  setYaml: (yaml) => set({ yaml, step: 'editor' }),
  setError: (error) => set({ error }),
  setSettings: (settings) => set({ settings }),
  appendThinking: (text) => set((s) => ({ thinking: s.thinking + text })),
  clearThinking: () => set({ thinking: '' }),
  reset: () =>
    set({
      step: 'upload',
      file: null,
      runId: null,
      progress: null,
      yaml: null,
      error: null,
      thinking: '',
      events: [],
      currentStage: null,
      settings: { script_type: 'tv', language: 'zh' },
    }),
}))
