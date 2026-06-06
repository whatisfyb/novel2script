import { create } from 'zustand'
import type {
  ConversionProgress,
  ConversionSettings,
  PipelineEvent,
  PipelineStageKey,
  User,
} from '@/types'

type Step = 'upload' | 'progress' | 'editor'

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

  // Auth actions (mock implementation)
  login: async (username, _password) => {
    await new Promise((resolve) => setTimeout(resolve, 500))
    set({ user: { id: 'mock-user', username }, token: 'mock-token-' + Date.now() })
  },
  register: async (username, email, _password) => {
    await new Promise((resolve) => setTimeout(resolve, 500))
    set({ user: { id: 'mock-user', username, email }, token: 'mock-token-' + Date.now() })
  },
  logout: () => {
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
