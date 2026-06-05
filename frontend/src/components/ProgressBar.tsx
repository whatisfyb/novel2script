import { Card, Typography, Space, Tag, Collapse } from 'antd'
import {
  LoadingOutlined, CheckCircleFilled,
  FileSearchOutlined, SplitCellsOutlined, UserSwitchOutlined,
  ApartmentOutlined, BuildOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import type { FC } from 'react'
import type { ConversionProgress } from '@/types'
import { useSessionStore } from '@/stores/session'

const { Title, Text, Paragraph } = Typography

const STAGES = [
  { key: 'parser', label: '解析文件', icon: <FileSearchOutlined /> },
  { key: 'splitter', label: '拆分章节', icon: <SplitCellsOutlined /> },
  { key: 'analyzer', label: '分析结构', icon: <UserSwitchOutlined /> },
  { key: 'segmenter', label: '提取场景', icon: <ApartmentOutlined /> },
  { key: 'assembler', label: '生成剧本', icon: <BuildOutlined /> },
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

  const stageIndex = STAGES.findIndex((s) => s.key === currentStage)

  return (
    <div className="max-w-xl mx-auto">
      {/* Progress bar */}
      <Card className="!rounded-2xl !border-0 !shadow-sm mb-4" styles={{ body: { padding: '24px' } }}>
        <div className="text-center mb-6">
          {isDone ? (
            <Space size="middle">
              <CheckCircleFilled className="text-4xl text-green-500" />
              <Title level={3} className="!mb-0 !text-green-600">转换完成！</Title>
            </Space>
          ) : (
            <Space size="middle">
              <LoadingOutlined className="text-4xl text-indigo-500" spin />
              <Title level={3} className="!mb-0 !text-gray-700">正在转换...</Title>
            </Space>
          )}
        </div>

        {/* Animated progress bar with gradient */}
        <div className="relative w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-4">
          <div
            className="absolute top-0 left-0 h-full rounded-full bg-indigo-500 transition-all duration-700 ease-out"
            style={{ width: `${percentage}%` }}
          />
          {/* Shimmer animation while processing */}
          {!isDone && percentage > 0 && (
            <div
              className="absolute top-0 left-0 h-full w-16 bg-gradient-to-r from-transparent via-white/20 to-transparent"
              style={{ left: `${Math.max(0, percentage - 10)}%` }}
            />
          )}
        </div>

        <div className="flex justify-between text-sm">
          <Text className="text-indigo-600 font-medium">{message}</Text>
          <Text className="text-gray-400 font-mono">{percentage}%</Text>
        </div>
      </Card>

      {/* Stage timeline */}
      <Card className="!rounded-2xl !border-0 !shadow-sm" styles={{ body: { padding: '20px 24px' } }}>
        <div className="space-y-0">
          {STAGES.map((stage, idx) => {
            const isActive = idx === stageIndex && !isDone
            const isComplete = (idx < stageIndex) || (isDone && idx === STAGES.length - 1)
            const isPending = idx > stageIndex && !isDone

            return (
              <div key={stage.key} className="flex items-start gap-3 py-2.5">
                {/* Icon with status */}
                <div className="flex flex-col items-center">
                  <div className={`
                    w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0
                    transition-all duration-500
                    ${isComplete ? 'bg-green-100 text-green-600' : ''}
                    ${isActive ? 'bg-indigo-100 text-indigo-600 ring-2 ring-indigo-300 ring-offset-2 animate-pulse' : ''}
                    ${isPending ? 'bg-gray-100 text-gray-300' : ''}
                  `}>
                    {isComplete ? <CheckCircleFilled className="text-lg" /> : (
                      isActive ? <LoadingOutlined className="text-lg" spin /> : stage.icon
                    )}
                  </div>
                  {/* Connector line (except last) */}
                  {idx < STAGES.length - 1 && (
                    <div className={`
                      w-0.5 h-6 my-1
                      ${isComplete ? 'bg-green-300' : 'bg-gray-200'}
                      transition-colors duration-500
                    `} />
                  )}
                </div>

                {/* Label */}
                <div className="flex-1 pt-1">
                  <Text
                    className={`
                      ${isComplete ? 'text-green-600' : ''}
                      ${isActive ? 'text-indigo-600 font-semibold' : ''}
                      ${isPending ? 'text-gray-300' : ''}
                      transition-colors duration-500
                    `}
                  >
                    {stage.label}
                  </Text>
                  {isActive && (
                    <Text type="secondary" className="block text-xs mt-0.5">
                      {message}
                    </Text>
                  )}
                </div>

                {/* Status badge */}
                <div className="pt-1">
                  {isComplete && <Tag color="success" className="!text-xs">完成</Tag>}
                  {isActive && <Tag color="processing" className="!text-xs">进行中</Tag>}
                  {isPending && <Tag className="!text-xs !text-gray-300 !border-gray-200">等待</Tag>}
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* AI Thinking panel — shows streaming LLM tokens */}
      {thinking && !isDone && (
        <Card
          className="!rounded-2xl !border-0 !shadow-sm mt-4"
          size="small"
          styles={{ body: { padding: '12px 16px' } }}
        >
          <Collapse
            ghost
            size="small"
            items={[{
              key: 'thinking',
              label: (
                <Space size={4}>
                  <BulbOutlined className="text-amber-500" />
                  <Text className="text-gray-500 text-sm">AI 思考中...</Text>
                  <Text type="secondary" className="text-xs">({thinking.length} 字)</Text>
                </Space>
              ),
              children: (
                <Paragraph
                  className="!mb-0 text-gray-500 text-sm whitespace-pre-wrap max-h-40 overflow-y-auto font-mono"
                >
                  {thinking}
                </Paragraph>
              ),
            }]}
          />
        </Card>
      )}
    </div>
  )
}

export default ProgressBar
