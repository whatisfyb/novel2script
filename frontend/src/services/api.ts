import type { UploadResponse, ConversionSettings, ConversionProgress } from '@/types'
import { MOCK_YAML, simulateProgress } from './mock'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const USE_MOCK = !API_BASE

export async function uploadFile(file: File): Promise<UploadResponse> {
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
  settings: ConversionSettings,
  onProgress: (p: ConversionProgress) => void,
  onThinking: (text: string) => void,
  onComplete: (yaml: string) => void,
  onError: (err: string) => void,
): Promise<void> {
  if (USE_MOCK) {
    simulateProgress(
      onProgress,
      () => onComplete(MOCK_YAML),
    )
    return
  }

  // Step 1: Start conversion and get job_id
  const convertRes = await fetch(`${API_BASE}/api/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, ...settings }),
  })

  if (!convertRes.ok) {
    onError(`Failed to start conversion: ${convertRes.statusText}`)
    return
  }

  const { job_id } = await convertRes.json()

  // Step 2: Connect to WebSocket with job_id
  const wsProtocol = API_BASE.startsWith('https') ? 'wss' : 'ws'
  const wsBase = API_BASE.replace(/^https?/, wsProtocol)
  const ws = new WebSocket(`${wsBase}/api/progress/${job_id}`)

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (msg.type === 'progress') {
      onProgress({
        stage: msg.stage,
        percentage: msg.progress ?? 0,
        message: msg.message || '处理中...',
        chapter: msg.chapter,
        total_chapters: msg.total_chapters,
      })
    } else if (msg.type === 'thinking') {
      onThinking(msg.text)
    } else if (msg.type === 'complete') {
      onComplete(msg.yaml)
      ws.close()
    } else if (msg.type === 'error') {
      onError(msg.error)
      ws.close()
    }
  }

  ws.onerror = () => onError('WebSocket connection failed')

  ws.onclose = () => {
    fetch(`${API_BASE}/api/result/${job_id}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.status === 'completed' && data.yaml) {
          onComplete(data.yaml)
        } else if (data.error) {
          onError(data.error)
        }
      })
      .catch(() => {})
  }
}
