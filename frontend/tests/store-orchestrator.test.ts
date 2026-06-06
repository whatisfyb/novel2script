/**
 * Tests for the session store — new fields and actions for the
 * multi-service orchestrator.
 */

import { beforeEach, describe, expect, it } from 'vitest'
import { useSessionStore } from '@/stores/session'

describe('session store — new orchestrator fields', () => {
  beforeEach(() => {
    useSessionStore.getState().reset()
  })

  it('starts with empty events and null runId', () => {
    const s = useSessionStore.getState()
    expect(s.runId).toBeNull()
    expect(s.events).toEqual([])
    expect(s.currentStage).toBeNull()
  })

  it('setRunId sets the run_id', () => {
    useSessionStore.getState().setRunId('r_123_abc')
    expect(useSessionStore.getState().runId).toBe('r_123_abc')
  })

  it('appendEvent appends to events list', () => {
    const e = {
      _id: '1', type: 'pipeline.started', source: 'orchestrator',
      correlation_id: 'r_1', ts: '1', payload: {}, metadata: {},
    }
    useSessionStore.getState().appendEvent(e)
    useSessionStore.getState().appendEvent({ ...e, _id: '2' })
    expect(useSessionStore.getState().events).toHaveLength(2)
  })

  it('clearEvents empties the list', () => {
    useSessionStore.getState().appendEvent({
      _id: '1', type: 't', source: 's',
      correlation_id: 'c', ts: '1', payload: {}, metadata: {},
    })
    useSessionStore.getState().clearEvents()
    expect(useSessionStore.getState().events).toEqual([])
  })

  it('setCurrentStage tracks 6-stage key', () => {
    useSessionStore.getState().setCurrentStage('extract')
    expect(useSessionStore.getState().currentStage).toBe('extract')
  })

  it('reset clears all orchestrator fields', () => {
    const s = useSessionStore.getState()
    s.setRunId('r_1')
    s.setCurrentStage('extract')
    s.appendEvent({
      _id: '1', type: 't', source: 's',
      correlation_id: 'c', ts: '1', payload: {}, metadata: {},
    })
    s.reset()
    const after = useSessionStore.getState()
    expect(after.runId).toBeNull()
    expect(after.events).toEqual([])
    expect(after.currentStage).toBeNull()
  })

  it('logout clears events + runId + currentStage', () => {
    const s = useSessionStore.getState()
    s.setRunId('r_1')
    s.setCurrentStage('segment')
    s.appendEvent({
      _id: '1', type: 't', source: 's',
      correlation_id: 'c', ts: '1', payload: {}, metadata: {},
    })
    s.logout()
    const after = useSessionStore.getState()
    expect(after.runId).toBeNull()
    expect(after.events).toEqual([])
    expect(after.currentStage).toBeNull()
  })
})
