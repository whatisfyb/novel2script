import type { HistoryRecord } from '@/types'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

/** Fetch history list from backend */
export async function fetchHistory(
  page: number = 1,
  size: number = 20,
  scriptType?: string,
  status?: string,
): Promise<{ items: HistoryRecord[]; total: number }> {
  const params = new URLSearchParams({ page: String(page), size: String(size) })
  if (scriptType && scriptType !== 'all') params.append('scriptType', scriptType)
  if (status) params.append('status', status)

  const res = await fetch(`${API_BASE}/api/history?${params}`)
  const json = await res.json()

  if (json.code !== 200) {
    throw new Error(json.message || 'Failed to fetch history')
  }

  return json.data
}

/** Get single record by runId */
export async function getHistoryByRunId(runId: string): Promise<HistoryRecord> {
  const res = await fetch(`${API_BASE}/api/history/${runId}`)
  const json = await res.json()

  if (json.code !== 200) {
    throw new Error(json.message || 'Failed to fetch record')
  }

  return json.data
}

/** Delete a record by runId */
export async function deleteHistoryRecord(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/history/${runId}`, { method: 'DELETE' })
  const json = await res.json()

  if (json.code !== 200) {
    throw new Error(json.message || 'Failed to delete record')
  }
}

/** Create a new history record (called by orchestrator after conversion) */
export async function createHistoryRecord(data: {
  runId: string
  filename: string
  title?: string
  scriptType: string
  language: string
}): Promise<HistoryRecord> {
  const res = await fetch(`${API_BASE}/api/history`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const json = await res.json()

  if (json.code !== 200) {
    throw new Error(json.message || 'Failed to create record')
  }

  return json.data
}

/** Update a history record (called by orchestrator when conversion completes/fails) */
export async function updateHistoryRecord(
  runId: string,
  data: Partial<Pick<HistoryRecord, 'status' | 'chapters' | 'acts' | 'scenes' | 'characters' | 'yaml' | 'error'>>,
): Promise<HistoryRecord> {
  const res = await fetch(`${API_BASE}/api/history/${runId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const json = await res.json()

  if (json.code !== 200) {
    throw new Error(json.message || 'Failed to update record')
  }

  return json.data
}
