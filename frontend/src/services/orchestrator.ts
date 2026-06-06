/**
 * Orchestrator API client — talks to the multi-service pipeline.
 *
 * Endpoints (new architecture):
 *   POST /pipeline                  → SubmitResponse { run_id }
 *   GET  /pipeline/{run_id}/status → RunStatus
 *   GET  /pipeline/{run_id}/events → { events: PipelineEvent[] }
 *   GET  /pipeline/{run_id}/result → RunResult { yaml }
 *   WS   /ws/pipeline/{run_id}     → live PipelineEvent stream
 *
 * Falls back to mock when no API base is set (e.g. during local dev without backend).
 */

import type {
  PipelineEvent,
  RunResult,
  RunStatus,
  SubmitResponse,
} from '@/types'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const USE_MOCK = !API_BASE

/** Submit a novel file. Returns run_id for tracking. */
export async function submitPipeline(file: File): Promise<SubmitResponse> {
  if (USE_MOCK) {
    return { run_id: `mock-${Date.now()}` }
  }
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/pipeline`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    throw new Error(`Submit failed: ${res.statusText}`)
  }
  return res.json()
}

/** Poll the current run status. Cheap (single Redis HGETALL). */
export async function getRunStatus(runId: string): Promise<RunStatus> {
  if (USE_MOCK) {
    // simulate progress
    const elapsed = Date.now() - Number(runId.replace('mock-', ''))
    const pct = Math.min(100, Math.floor(elapsed / 200))
    if (pct >= 100) return { stage: 'done', progress: '100' }
    return { stage: 'input', progress: String(pct) }
  }
  const res = await fetch(`${API_BASE}/pipeline/${runId}/status`)
  if (!res.ok) {
    throw new Error(`Status failed: ${res.statusText}`)
  }
  return res.json()
}

/** Fetch audit-trail events (most recent first). */
export async function getRunEvents(
  runId: string,
  count: number = 100,
): Promise<PipelineEvent[]> {
  if (USE_MOCK) return []
  const res = await fetch(
    `${API_BASE}/pipeline/${runId}/events?count=${count}`,
  )
  if (!res.ok) {
    throw new Error(`Events failed: ${res.statusText}`)
  }
  const data = await res.json()
  return data.events ?? []
}

/** Fetch final YAML result. Returns null if not yet ready. */
export async function getRunResult(runId: string): Promise<string | null> {
  if (USE_MOCK) {
    return 'meta:\n  title: mock\nscenes: []\n'
  }
  const res = await fetch(`${API_BASE}/pipeline/${runId}/result`)
  if (res.status === 404) return null
  if (!res.ok) {
    throw new Error(`Result failed: ${res.statusText}`)
  }
  const data: RunResult = await res.json()
  return data.yaml
}

/** Open a WebSocket to the orchestrator's live event stream.
 *  Returns a cleanup function. The callback receives each event as it arrives. */
export function subscribeRunEvents(
  runId: string,
  onEvent: (event: PipelineEvent) => void,
  onError?: (err: string) => void,
): () => void {
  if (USE_MOCK) {
    // Mock subscription — emit a fake event every 2s
    const interval = setInterval(() => {
      onEvent({
        _id: `mock-${Date.now()}`,
        type: 'mock.event',
        source: 'mock',
        correlation_id: '',
        ts: String(Date.now() / 1000),
        payload: {},
        metadata: {},
      })
    }, 2000)
    return () => clearInterval(interval)
  }

  const wsProtocol = API_BASE.startsWith('https') ? 'wss' : 'ws'
  const wsBase = API_BASE.replace(/^https?/, wsProtocol)
  const ws = new WebSocket(`${wsBase}/ws/pipeline/${runId}`)

  ws.onmessage = (e) => {
    try {
      const event: PipelineEvent = JSON.parse(e.data)
      onEvent(event)
    } catch (err) {
      onError?.(`Failed to parse event: ${err}`)
    }
  }
  ws.onerror = () => onError?.('WebSocket connection failed')

  return () => {
    try { ws.close() } catch { /* ignore */ }
  }
}

/** One-shot conversion: submit, subscribe, return final YAML.
 *  Calls onProgress at each stage transition; onEvent for audit trail. */
export async function runConversion(
  file: File,
  onEvent: (event: PipelineEvent) => void,
  onError: (err: string) => void,
): Promise<{ runId: string; yaml: string }> {
  const { run_id } = await submitPipeline(file)
  const unsubscribe = subscribeRunEvents(run_id, onEvent, onError)

  // Poll status until done or failed
  let lastStatus: RunStatus | null = null
  for (let i = 0; i < 600; i++) {  // max 10 minutes (1s intervals)
    await new Promise((r) => setTimeout(r, 1000))
    let status: RunStatus
    try {
      status = await getRunStatus(run_id)
    } catch (e) {
      continue
    }
    if (status !== lastStatus) {
      lastStatus = status
    }
    if (status.stage === 'done') {
      unsubscribe()
      const yaml = await getRunResult(run_id)
      return { runId: run_id, yaml: yaml ?? '' }
    }
    if (status.stage && status.stage.startsWith('failed')) {
      unsubscribe()
      throw new Error(status.error || `Pipeline failed: ${status.stage}`)
    }
  }
  unsubscribe()
  throw new Error('Pipeline timed out after 10 minutes')
}
