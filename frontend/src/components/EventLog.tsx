import { useMemo } from 'react'
import { Card, Typography, Tag, Tooltip, Badge } from 'antd'
import {
  ApiOutlined, ClockCircleOutlined, PartitionOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons'
import type { FC } from 'react'
import type { PipelineEvent } from '@/types'
import { useSessionStore } from '@/stores/session'

const { Text } = Typography

const SOURCE_META: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  orchestrator:      { color: 'blue',   icon: <PartitionOutlined />,    label: '编排' },
  input_service:     { color: 'cyan',   icon: <ApiOutlined />,          label: '输入' },
  structure_service: { color: 'purple', icon: <ApiOutlined />,          label: '结构' },
  beat_service:      { color: 'magenta',icon: <NodeIndexOutlined />,    label: '节拍' },
  mock:              { color: 'default',icon: <ClockCircleOutlined />,  label: '模拟' },
}

const formatTime = (ts: string) => {
  const n = Number(ts)
  if (!Number.isFinite(n) || n <= 0) return '—'
  const d = new Date(n * 1000)
  return d.toLocaleTimeString('zh-CN', { hour12: false }) +
    `.${String(d.getMilliseconds()).padStart(3, '0')}`
}

const summarizePayload = (event: PipelineEvent): string => {
  const p = event.payload || {}
  // Show the most useful field per event type
  if (typeof p.n_beats === 'number') return `${p.n_beats} 节拍`
  if (typeof p.n_scenes === 'number') return `${p.n_scenes} 场景`
  if (typeof p.n_chapters === 'number') return `${p.n_chapters} 章节`
  if (typeof p.n_characters === 'number') return `${p.n_characters} 角色`
  if (typeof p.n_corrections === 'number') return `${p.n_corrections} 修正`
  if (typeof p.filename === 'string') return p.filename
  if (typeof p.scene_id === 'string') return p.scene_id
  if (typeof p.error === 'string') return p.error
  if (typeof p.message === 'string') return p.message
  return ''
}

interface Props {
  maxHeight?: number
}

const EventLog: FC<Props> = ({ maxHeight = 320 }) => {
  const events = useSessionStore((s) => s.events)

  // Reverse so newest is at top, but cap to recent N for perf
  const recent = useMemo(() => {
    return [...events].reverse().slice(0, 200)
  }, [events])

  return (
    <Card
      className="!rounded-2xl !border-0 !shadow-sm"
      title={
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Text strong>事件日志</Text>
            <Badge
              count={events.length}
              overflowCount={999}
              size="small"
              style={{ backgroundColor: 'var(--accent-700)' }}
            />
          </div>
          <Text type="secondary" className="text-xs">Redis Stream 审计追踪</Text>
        </div>
      }
      size="small"
      styles={{ body: { padding: 0 } }}
    >
      {recent.length === 0 ? (
        <div className="text-center text-gray-400 py-8 text-sm">
          暂无事件 — 提交小说后此处会实时显示每个步骤
        </div>
      ) : (
        <div
          className="overflow-y-auto px-4 py-2"
          style={{ maxHeight }}
        >
          {recent.map((e) => {
            const meta = SOURCE_META[e.source] ?? SOURCE_META.mock
            return (
              <div
                key={e._id}
                className="flex items-start gap-2 py-2 border-b border-gray-50 last:border-0"
              >
                <Tag color={meta.color} className="!text-xs !m-0 flex-shrink-0">
                  <span className="inline-flex items-center gap-1">
                    {meta.icon}
                    {meta.label}
                  </span>
                </Tag>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <Text className="text-xs font-mono text-gray-700">{e.type}</Text>
                    {e.correlation_id && (
                      <Text type="secondary" className="text-xs">
                        {e.correlation_id}
                      </Text>
                    )}
                  </div>
                  {summarizePayload(e) && (
                    <div
                      className="text-xs text-gray-500 truncate leading-relaxed"
                      title={summarizePayload(e)}
                    >
                      {summarizePayload(e)}
                    </div>
                  )}
                </div>
                <Tooltip title={new Date(Number(e.ts) * 1000).toLocaleString('zh-CN')}>
                  <Text type="secondary" className="text-xs font-mono flex-shrink-0">
                    {formatTime(e.ts)}
                  </Text>
                </Tooltip>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}

export default EventLog
