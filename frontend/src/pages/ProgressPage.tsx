import { useEffect, useRef } from 'react'
import { Button } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import type { FC } from 'react'
import ProgressBar from '@/components/ProgressBar'
import { useSessionStore } from '@/stores/session'
import { startConversion } from '@/services/api'
import type { ConversionSettings } from '@/types'

interface Props {
  settings: ConversionSettings
  onComplete: () => void
  onCancel: () => void
}

const ProgressPage: FC<Props> = ({ settings, onComplete, onCancel }) => {
  const { file, sessionId, updateProgress, setYaml, setError, appendThinking } = useSessionStore()
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    startConversion(
      sessionId || 'mock',
      settings,
      (p) => updateProgress(p),
      (t) => appendThinking(t),
      (yaml) => setYaml(yaml),
      (err) => setError(err),
    )
  }, [])

  // Navigate to editor when complete
  const progress = useSessionStore((s) => s.progress)
  useEffect(() => {
    if (progress?.percentage === 100) {
      const timer = setTimeout(onComplete, 1500)
      return () => clearTimeout(timer)
    }
  }, [progress?.percentage, onComplete])

  return (
    <div className="max-w-4xl mx-auto px-4 pt-12 pb-24">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          AI 正在转换你的剧本
        </h1>
        <p className="text-gray-400">{file?.name}</p>
      </div>

      <ProgressBar progress={progress} />

      <div className="text-center mt-6">
        <Button icon={<ArrowLeftOutlined />} onClick={onCancel} type="text" className="text-gray-400">
          取消并重新选择
        </Button>
      </div>
    </div>
  )
}

export default ProgressPage
