import { Typography, Space, Collapse } from 'antd'
import {
  LoadingOutlined,
  CheckCircleFilled,
  FileSearchOutlined,
  SplitCellsOutlined,
  UserSwitchOutlined,
  ApartmentOutlined,
  ThunderboltOutlined,
  BuildOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import type { FC, ReactNode } from 'react'
import type { ConversionProgress, PipelineStageKey } from '@/types'
import { useSessionStore } from '@/stores/session'

const { Title, Text, Paragraph } = Typography

// 6-stage granular timeline per project spec:
//   解析(parse) → 拆分(split) → 分析(analyze) → 提取场景(segment) → 抽取节拍(extract) → 装配剧本(assemble)
const STAGES: { key: PipelineStageKey; label: string; icon: ReactNode }[] = [
  { key: 'parse',    label: '解析文件',     icon: <FileSearchOutlined /> },
  { key: 'split',    label: '拆分章节',     icon: <SplitCellsOutlined /> },
  { key: 'analyze',  label: '分析结构',     icon: <UserSwitchOutlined /> },
  { key: 'segment',  label: '提取场景',     icon: <ApartmentOutlined /> },
  { key: 'extract',  label: '抽取节拍',     icon: <ThunderboltOutlined /> },
  { key: 'assemble', label: '生成剧本',     icon: <BuildOutlined /> },
]

interface Props {
  progress: ConversionProgress | null
}

const ProgressBar: FC<Props> = ({ progress }) => {
  const percentage = progress?.percentage ?? 0
  const currentStage = progress?.stage ?? ''
  const message = progress?.message ?? '准备中...'
  const isDone = percentage >= 100
  const thinking = useSessionStore((s) => s.thinking)

  // Match by service-level stage (input / structure / beat / assemble) to granular stage key
  const stageFromService = (s: string): PipelineStageKey | null => {
    if (s === 'input' || s === 'input_done') return 'parse'
    if (s === 'structure' || s === 'structure_analyzed') return 'analyze'
    if (s === 'structure_done' || s === 'segment') return 'segment'
    if (s === 'beat' || s === 'beat_done') return 'extract'
    if (s === 'assemble' || s === 'done') return 'assemble'
    if (s === 'starting') return 'parse'
    return null
  }

  const activeKey = stageFromService(currentStage) ?? currentStage as PipelineStageKey
  const stageIndex = STAGES.findIndex((s) => s.key === activeKey)

  return (
    <div className="max-w-xl mx-auto">
      {/* Progress card */}
      <div
        className="mb-4 p-6"
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div className="text-center mb-6">
          {isDone ? (
            <Space size="middle">
              <CheckCircleFilled style={{ fontSize: 32, color: 'var(--accent-700)' }} />
              <Title
                level={3}
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'var(--accent-700)',
                  marginBottom: 0,
                }}
              >
                转换完成
              </Title>
            </Space>
          ) : (
            <Space size="middle">
              <LoadingOutlined style={{ fontSize: 32, color: 'var(--ink-900)' }} spin />
              <Title
                level={3}
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'var(--ink-900)',
                  marginBottom: 0,
                }}
              >
                正在转换...
              </Title>
            </Space>
          )}
        </div>

        {/* Progress bar — solid ink, no gradient */}
        <div
          className="relative w-full rounded-full overflow-hidden mb-4"
          style={{
            height: 6,
            backgroundColor: 'var(--ink-100)',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              height: '100%',
              borderRadius: 9999,
              backgroundColor: 'var(--ink-900)',
              transition: 'width 0.7s cubic-bezier(0.4, 0, 0.2, 1)',
              width: `${percentage}%`,
            }}
          />
        </div>

        <div className="flex justify-between text-sm">
          <Text style={{ color: 'var(--accent-700)', fontWeight: 500 }}>{message}</Text>
          <Text
            style={{
              color: 'var(--ink-500)',
              fontFamily: 'var(--font-mono)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {percentage}%
          </Text>
        </div>
      </div>

      {/* Stage timeline (6 stages) */}
      <div
        className="p-6"
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          boxShadow: 'var(--shadow-xs)',
        }}
      >
        <div className="space-y-0">
          {STAGES.map((stage, idx) => {
            const isActive = idx === stageIndex && !isDone
            const isComplete = (idx < stageIndex) || (isDone && idx === STAGES.length - 1)

            return (
              <div key={stage.key} className="flex items-start gap-3 py-2.5">
                {/* Icon with status */}
                <div className="flex flex-col items-center">
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      transition: 'all 0.4s ease',
                      backgroundColor: 'var(--ink-100)',
                      color: isComplete
                        ? 'var(--accent-700)'
                        : isActive
                          ? 'var(--ink-900)'
                          : 'var(--ink-300)',
                      ...(isComplete ? { backgroundColor: 'var(--accent-100)' } : {}),
                      ...(isActive ? { boxShadow: '0 0 0 3px var(--bg-primary), 0 0 0 5px var(--ink-300)' } : {}),
                    }}
                  >
                    {isComplete ? (
                      <CheckCircleFilled style={{ fontSize: 14 }} />
                    ) : isActive ? (
                      <LoadingOutlined style={{ fontSize: 14 }} spin />
                    ) : (
                      stage.icon
                    )}
                  </div>
                  {/* Connector line */}
                  {idx < STAGES.length - 1 && (
                    <div
                      style={{
                        width: 1.5,
                        height: 24,
                        marginTop: 4,
                        marginBottom: 4,
                        backgroundColor: isComplete ? 'var(--accent-500)' : 'var(--ink-100)',
                        transition: 'background-color 0.3s ease',
                      }}
                    />
                  )}
                </div>

                {/* Label + status */}
                <div className="flex-1 pt-1.5">
                  <Text
                    style={{
                      fontSize: 13,
                      fontWeight: isComplete || isActive ? 600 : 400,
                      color: isComplete || isActive ? 'var(--ink-900)' : 'var(--ink-300)',
                      transition: 'color 0.3s ease',
                    }}
                  >
                    {stage.label}
                  </Text>
                  {isActive && message && (
                    <div
                      style={{
                        fontSize: 11,
                        color: 'var(--ink-500)',
                        marginTop: 2,
                      }}
                    >
                      {message}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* AI Thinking panel */}
      {thinking && !isDone && (
        <div
          className="mt-4 px-4 py-3"
          style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 10,
            boxShadow: 'var(--shadow-xs)',
          }}
        >
          <Collapse
            ghost
            size="small"
            items={[{
              key: 'thinking',
              label: (
                <Space size={4}>
                  <BulbOutlined style={{ color: 'var(--accent-500)' }} />
                  <Text style={{ color: 'var(--ink-500)', fontSize: 13 }}>
                    AI 思考中...
                  </Text>
                  <Text style={{ fontSize: 11, color: 'var(--ink-300)' }}>
                    ({thinking.length} 字)
                  </Text>
                </Space>
              ),
              children: (
                <Paragraph
                  style={{
                    marginBottom: 0,
                    color: 'var(--ink-500)',
                    fontSize: 12,
                    fontFamily: 'var(--font-mono)',
                    whiteSpace: 'pre-wrap',
                    maxHeight: 160,
                    overflowY: 'auto',
                  }}
                >
                  {thinking}
                </Paragraph>
              ),
            }]}
          />
        </div>
      )}
    </div>
  )
}

export default ProgressBar
