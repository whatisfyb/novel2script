/**
 * Legacy API client — kept for backward compatibility with the old
 * monolithic pipeline (POST /api/upload + /api/convert + /api/progress).
 *
 * New code should use `services/orchestrator.ts` which talks to the
 * multi-service architecture.
 */

import { MOCK_YAML, simulateProgress } from './mock'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const USE_MOCK = !API_BASE

export interface LegacyUploadResponse {
  session_id: string
  filename: string
  chapters_detected?: number
}

export async function uploadFile(file: File): Promise<LegacyUploadResponse> {
  if (USE_MOCK) {
    return {
      session_id: `mock-${Date.now()}`,
      filename: file.name,
      chapters_detected: 3,
    }
  }
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: formData })
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
  return res.json()
}

export async function startConversion(
  sessionId: string,
  settings: Record<string, unknown>,
  onProgress: (p: unknown) => void,
  onThinking: (text: string) => void,
  onComplete: (yaml: string) => void,
  onError: (err: string) => void,
): Promise<void> {
  if (USE_MOCK) {
    simulateProgress(onProgress as never, () => onComplete(MOCK_YAML))
    return
  }
  // Legacy path — not used by new code.
  void sessionId; void settings; void onThinking
  onError('Legacy /api/convert endpoint removed. Use services/orchestrator.ts')
}
