import { describe, it, expect, beforeEach } from 'vitest'
import { useSessionStore } from '@/stores/session'

describe('Session Store', () => {
  beforeEach(() => {
    useSessionStore.getState().reset()
  })

  it('should start with idle state', () => {
    const state = useSessionStore.getState()
    expect(state.step).toBe('upload')
    expect(state.yaml).toBeNull()
  })

  it('should set uploaded file', () => {
    useSessionStore.getState().setFile({ name: 'test.txt', size: 1000 } as File)
    expect(useSessionStore.getState().file?.name).toBe('test.txt')
  })

  it('should transition to progress step', () => {
    useSessionStore.getState().setStep('progress')
    expect(useSessionStore.getState().step).toBe('progress')
  })

  it('should update progress', () => {
    useSessionStore.getState().updateProgress({ percentage: 50, message: 'Processing chapter 3' })
    expect(useSessionStore.getState().progress?.percentage).toBe(50)
  })

  it('should set yaml and transition to editor', () => {
    const yaml = 'meta:\n  title: Test'
    useSessionStore.getState().setYaml(yaml)
    expect(useSessionStore.getState().yaml).toBe(yaml)
    expect(useSessionStore.getState().step).toBe('editor')
  })

  it('should reset to initial state', () => {
    useSessionStore.getState().setFile({ name: 'test.txt' } as File)
    useSessionStore.getState().setStep('progress')
    useSessionStore.getState().reset()
    expect(useSessionStore.getState().step).toBe('upload')
    expect(useSessionStore.getState().file).toBeNull()
  })
})
