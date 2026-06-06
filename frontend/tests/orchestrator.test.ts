/**
 * Tests for the orchestrator service — new multi-service API client.
 *
 * The module reads `import.meta.env.VITE_API_BASE` at import time, so we
 * use vi.resetModules() + dynamic import to swap the env var per test.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const originalFetch = globalThis.fetch
const originalWS = (globalThis as unknown as { WebSocket?: unknown }).WebSocket

afterEach(() => {
  globalThis.fetch = originalFetch
  if (originalWS) (globalThis as unknown as { WebSocket: unknown }).WebSocket = originalWS
  vi.unstubAllEnvs()
  vi.resetModules()
})

/** Re-imports the orchestrator module after stubbing env vars. */
async function importOrchestrator() {
  return await import('@/services/orchestrator')
}

describe('orchestrator — with API_BASE set', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE', 'http://test-api')
  })

  it('submitPipeline POSTs to /pipeline and returns run_id', async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe('http://test-api/pipeline')
      expect(init?.method).toBe('POST')
      return new Response(JSON.stringify({ run_id: 'r_123' }), { status: 200 })
    })
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const mod = await importOrchestrator()
    const res = await mod.submitPipeline(new File(['x'], 'x.txt'))
    expect(res.run_id).toBe('r_123')
  })

  it('submitPipeline throws on 5xx', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response('boom', { status: 500, statusText: 'Server Error' }),
    ) as unknown as typeof fetch
    const mod = await importOrchestrator()
    await expect(mod.submitPipeline(new File(['x'], 'x.txt'))).rejects.toThrow(/Submit failed/)
  })

  it('getRunStatus returns hash fields', async () => {
    globalThis.fetch = vi.fn(async (url: string) => {
      expect(url).toBe('http://test-api/pipeline/r_1/status')
      return new Response(
        JSON.stringify({ stage: 'beat', progress: '60', updated_at: '123' }),
        { status: 200 },
      )
    }) as unknown as typeof fetch
    const mod = await importOrchestrator()
    const s = await mod.getRunStatus('r_1')
    expect(s.stage).toBe('beat')
    expect(s.progress).toBe('60')
  })

  it('getRunEvents returns events array', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          events: [{ _id: 'a', type: 'pipeline.started', source: 'orchestrator',
                     correlation_id: 'r_1', ts: '1', payload: {}, metadata: {} }],
        }),
        { status: 200 },
      ),
    ) as unknown as typeof fetch
    const mod = await importOrchestrator()
    const events = await mod.getRunEvents('r_1', 10)
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('pipeline.started')
  })

  it('getRunResult returns yaml on 200', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify({ yaml: 'meta: {}' }), { status: 200 }),
    ) as unknown as typeof fetch
    const mod = await importOrchestrator()
    expect(await mod.getRunResult('r_1')).toBe('meta: {}')
  })

  it('getRunResult returns null on 404', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response('not found', { status: 404 }),
    ) as unknown as typeof fetch
    const mod = await importOrchestrator()
    expect(await mod.getRunResult('r_1')).toBeNull()
  })

  it('runConversion submits, polls to done, returns yaml', async () => {
    let pollCount = 0
    globalThis.fetch = vi.fn(async (url: string) => {
      if (url === 'http://test-api/pipeline') {
        return new Response(JSON.stringify({ run_id: 'r_x' }), { status: 200 })
      }
      if (url === 'http://test-api/pipeline/r_x/status') {
        pollCount++
        const stage = pollCount < 2 ? 'structure' : 'done'
        return new Response(JSON.stringify({ stage, progress: '30' }), { status: 200 })
      }
      if (url === 'http://test-api/pipeline/r_x/result') {
        return new Response(JSON.stringify({ yaml: 'final' }), { status: 200 })
      }
      throw new Error('unexpected: ' + url)
    }) as unknown as typeof fetch
    // Make setTimeout fire immediately
    const orig = globalThis.setTimeout
    globalThis.setTimeout = ((fn: () => void) => { fn(); return 0 }) as unknown as typeof setTimeout

    const mod = await importOrchestrator()
    const { runId, yaml } = await mod.runConversion(
      new File(['x'], 'x.txt'), () => {}, () => {},
    )
    globalThis.setTimeout = orig

    expect(runId).toBe('r_x')
    expect(yaml).toBe('final')
  })

  it('runConversion throws on failed status', async () => {
    globalThis.fetch = vi.fn(async (url: string) => {
      if (url === 'http://test-api/pipeline') {
        return new Response(JSON.stringify({ run_id: 'r_y' }), { status: 200 })
      }
      if (url === 'http://test-api/pipeline/r_y/status') {
        return new Response(
          JSON.stringify({ stage: 'failed:orchestrator', progress: '50', error: 'LLM down' }),
          { status: 200 },
        )
      }
      throw new Error('unexpected')
    }) as unknown as typeof fetch
    const orig = globalThis.setTimeout
    globalThis.setTimeout = ((fn: () => void) => { fn(); return 0 }) as unknown as typeof setTimeout

    const mod = await importOrchestrator()
    await expect(
      mod.runConversion(new File(['x'], 'x.txt'), () => {}, () => {}),
    ).rejects.toThrow(/LLM down/)
    globalThis.setTimeout = orig
  })
})

describe('orchestrator — without API_BASE (mock mode)', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE', '')
  })

  it('submitPipeline returns mock run_id', async () => {
    const mod = await importOrchestrator()
    const res = await mod.submitPipeline(new File(['x'], 'x.txt'))
    expect(res.run_id).toMatch(/^mock-/)
  })

  it('getRunResult returns mock yaml', async () => {
    const mod = await importOrchestrator()
    const yaml = await mod.getRunResult('r_1')
    expect(yaml).toContain('scenes:')
  })

  it('getRunStatus returns simulated progress', async () => {
    const mod = await importOrchestrator()
    const s = await mod.getRunStatus('mock-' + (Date.now() - 1000))
    expect(['input', 'done']).toContain(s.stage)
  })

  it('subscribeRunEvents returns cleanup that does not throw', async () => {
    const mod = await importOrchestrator()
    const cleanup = mod.subscribeRunEvents('r_1', () => {}, () => {})
    expect(typeof cleanup).toBe('function')
    expect(() => cleanup()).not.toThrow()
  })
})
