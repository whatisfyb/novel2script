import { Button, Col, Row, Typography, message } from 'antd'
import {
  RocketOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  ApartmentOutlined,
} from '@ant-design/icons'
import type { FC } from 'react'
import { useCallback, useState } from 'react'
import { useSessionStore } from '@/stores/session'
import FileUploader from '@/components/FileUploader'
import SettingsPanel from '@/components/SettingsPanel'
import type { ConversionSettings } from '@/types'

const { Title, Text } = Typography

const features = [
  {
    icon: <FileTextOutlined />,
    title: '多格式解析',
    desc: '支持 .txt / .md / .docx 小说文本上传',
  },
  {
    icon: <ThunderboltOutlined />,
    title: '智能结构分析',
    desc: 'AI 自动识别人物、场景、对话节拍',
  },
  {
    icon: <ApartmentOutlined />,
    title: '结构化输出',
    desc: '标准 YAML 格式，可编辑可导出',
  },
]

interface Props {
  settings: ConversionSettings
  onSettingsChange: (s: ConversionSettings) => void
  onStart: () => void
}

const UploadPage: FC<Props> = ({ settings, onSettingsChange, onStart }) => {
  const { setFile } = useSessionStore()
  const [loading, setLoading] = useState(false)

  const handleFileSelected = useCallback((file: File) => {
    setFile(file)
    message.success(`已选择: ${file.name}`)
  }, [setFile])

  const handleStart = async () => {
    const { file } = useSessionStore.getState()
    if (!file) {
      message.warning('请先上传小说文件')
      return
    }
    setLoading(true)
    try {
      // With the orchestrator, no separate upload step — file is sent when
      // conversion starts. Just transition to the progress page.
      onStart()
    } catch (err) {
      message.error(`启动失败: ${err}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="max-w-4xl mx-auto px-6"
      style={{ minHeight: 'calc(100vh - 120px)' }}
    >
      {/* Hero — editorial style */}
      <div className="text-center pt-16 pb-10 fade-up">
        <div
          className="inline-block mb-4 px-3 py-1 text-xs tracking-widest uppercase"
          style={{
            backgroundColor: 'var(--accent-100)',
            color: 'var(--accent-700)',
            borderRadius: 3,
            fontWeight: 600,
            letterSpacing: '0.1em',
          }}
        >
          AI · Screenplay Pipeline
        </div>
        <Title
          level={1}
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '2.75rem',
            fontWeight: 700,
            color: 'var(--ink-900)',
            marginBottom: 12,
            lineHeight: 1.15,
            letterSpacing: '-0.02em',
          }}
        >
          把小说变成
          <span style={{ color: 'var(--accent-700)', fontStyle: 'italic' }}> 剧本</span>
        </Title>
        <Text
          style={{
            fontSize: 17,
            color: 'var(--ink-500)',
            fontFamily: 'var(--font-body)',
          }}
        >
          上传小说文本，AI 自动分析结构、提取角色与场景
          <br />
          生成专业 YAML 格式剧本
        </Text>
      </div>

      {/* Feature cards — minimal, border-focused */}
      <Row gutter={[20, 20]} className="mb-10 fade-up fade-up-delay-1">
        {features.map((f) => (
          <Col key={f.title} span={8}>
            <div
              className="surface-card p-6 h-full"
              style={{ borderRadius: 8 }}
            >
              <div className="mb-4 flex items-center gap-2">
                <span
                  className="text-xl"
                  style={{ color: 'var(--accent-700)' }}
                >
                  {f.icon}
                </span>
                <span className="accent-dot" />
              </div>
              <Text
                strong
                style={{
                  display: 'block',
                  marginBottom: 6,
                  fontSize: 15,
                  color: 'var(--ink-900)',
                }}
              >
                {f.title}
              </Text>
              <Text
                style={{
                  fontSize: 13,
                  color: 'var(--ink-500)',
                  lineHeight: 1.6,
                }}
              >
                {f.desc}
              </Text>
            </div>
          </Col>
        ))}
      </Row>

      {/* Upload area */}
      <div className="fade-up fade-up-delay-2">
        <FileUploader onFileSelected={handleFileSelected} />
      </div>

      {/* Settings */}
      <div className="fade-up fade-up-delay-2">
        <SettingsPanel settings={settings} onChange={onSettingsChange} />
      </div>

      {/* CTA — prominent, warm */}
      <div className="text-center mt-10 pb-16 fade-up fade-up-delay-3">
        <Button
          size="large"
          icon={<RocketOutlined />}
          loading={loading}
          onClick={handleStart}
          style={{
            height: 52,
            paddingInline: 40,
            fontSize: 16,
            fontWeight: 600,
            borderRadius: 8,
            backgroundColor: 'var(--ink-900)',
            borderColor: 'var(--ink-900)',
            color: '#fff',
            boxShadow: '0 4px 16px rgba(28, 25, 23, 0.15)',
          }}
        >
          开始转换
        </Button>
        <div
          className="mt-4 text-xs"
          style={{ color: 'var(--ink-500)', letterSpacing: '0.05em' }}
        >
          转换过程约 2-5 分钟 · 支持 WebSocket 实时进度
        </div>
      </div>
    </div>
  )
}

export default UploadPage
