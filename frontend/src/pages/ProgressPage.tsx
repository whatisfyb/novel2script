import { useEffect, useRef } from 'react'
import { Button } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import type { FC } from 'react'
import ProgressBar from '@/components/ProgressBar'
import EventLog from '@/components/EventLog'
import { useSessionStore } from '@/stores/session'
import {
  subscribeRunEvents,
  submitPipeline,
  getRunResult,
  getRunStatus,
} from '@/services/orchestrator'
import type { ConversionSettings, PipelineEvent } from '@/types'

interface Props {
  settings: ConversionSettings
  onComplete: () => void
  onCancel: () => void
}

/** Map a backend service-level stage to a frontend ConversionProgress.
 *  Status fields stored in Redis (pipeline:status:{run_id}):
 *    stage ∈ { starting, input, structure, structure_analyzed, structure_done,
 *              beat, assemble, done, failed:... }
 */
const stageToProgress = (stage: string, progress: string) => {
  const pct = Number(progress) || 0
  const stageLabelMap: Record<string, string> = {
    starting: '准备中...',
    input: '正在解析文件...',
    input_done: '文件解析完成',
    structure: '正在分析结构...',
    structure_analyzed: '结构分析完成',
    structure_done: '场景提取完成',
    beat: '正在抽取节拍...',
    beat_done: '节拍抽取完成',
    assemble: '正在生成剧本...',
    done: '转换完成！',
  }
  return {
    stage,
    percentage: pct,
    message: stageLabelMap[stage] ?? '处理中...',
  }
}

/** Map a backend event_type to a frontend stage key for the 6-stage timeline. */
const eventToStage = (eventType: string): string | null => {
  if (eventType === 'input.parsed' || eventType === 'stage.input.started') return 'input'
  if (eventType === 'input.split_done') return 'split'
  if (eventType === 'structure.analyzed' || eventType === 'stage.structure.started') return 'analyze'
  if (eventType === 'structure.segmented') return 'segment'
  if (eventType === 'beats.finalized' || eventType === 'stage.beat.started') return 'extract'
  if (eventType === 'pipeline.completed' || eventType === 'stage.assemble.started') return 'assemble'
  return null
}

const ProgressPage: FC<Props> = ({ onComplete, onCancel }) => {
  const {
    file, runId, setRunId, updateProgress, setCurrentStage,
    appendEvent, clearEvents, setYaml, setError,
  } = useSessionStore()
  const startedRef = useRef(false)
  const completedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current || !file) return
    startedRef.current = true
    clearEvents()

    const run = async () => {
      try {
        // 1. Submit file → get run_id
        const { run_id } = await submitPipeline(file)
        setRunId(run_id)

        // 2. Subscribe to live event stream
        const unsubscribe = subscribeRunEvents(
          run_id,
          (event: PipelineEvent) => {
            appendEvent(event)
            const stage = eventToStage(event.type)
            if (stage) setCurrentStage(stage as never)
          },
          (err) => setError(err),
        )

        // 3. Poll status until done
        while (!completedRef.current) {
          await new Promise((r) => setTimeout(r, 1500))
          const status = await getRunStatus(run_id)
          updateProgress(stageToProgress(status.stage, status.progress))
          if (status.stage === 'done') {
            completedRef.current = true
            break
          }
          if (status.stage?.startsWith('failed')) {
            throw new Error(status.error || `Pipeline failed: ${status.stage}`)
          }
        }

        unsubscribe()

        // 4. Fetch final YAML
        const yaml = await getRunResult(run_id)
        if (yaml) {
          setYaml(yaml)
        } else {
          throw new Error('Result not found after completion')
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        setError(msg)
      }
    }

    void run()
  }, [file])

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
        <p className="text-gray-400">{file?.name}{runId ? ` · run ${runId}` : ''}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ProgressBar progress={progress} />
        <EventLog maxHeight={420} />
      </div>

      <div className="text-center mt-6">
        <Button icon={<ArrowLeftOutlined />} onClick={onCancel} type="text" className="text-gray-400">
          取消并重新选择
        </Button>
      </div>
    </div>
  )
}

export default ProgressPage
