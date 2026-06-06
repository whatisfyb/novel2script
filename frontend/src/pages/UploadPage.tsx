import { useState, useCallback } from 'react'
import { Button, Typography, message, Card, Row, Col } from 'antd'
import {
  RocketOutlined, FileTextOutlined, SplitCellsOutlined,
  ApartmentOutlined,
} from '@ant-design/icons'
import type { FC } from 'react'
import FileUploader from '@/components/FileUploader'
import SettingsPanel from '@/components/SettingsPanel'
import { useSessionStore } from '@/stores/session'
import type { ConversionSettings } from '@/types'

const { Title, Text } = Typography

interface Props {
  settings: ConversionSettings
  onSettingsChange: (settings: ConversionSettings) => void
  onStart: () => void
}

const features = [
  { icon: <FileTextOutlined />, title: '智能解析', desc: '自动识别章节、人物、场景结构' },
  { icon: <SplitCellsOutlined />, title: '场景分割', desc: '精准切分每个场景与对话节拍' },
  { icon: <ApartmentOutlined />, title: '结构化输出', desc: '标准 YAML 格式，可编辑可导出' },
]

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
    <div className="max-w-4xl mx-auto px-4" style={{ minHeight: 'calc(100vh - 120px)' }}>
      {/* Hero section */}
      <div className="text-center pt-12 pb-8">
        <Title className="!text-4xl !font-bold !mb-3 !text-gray-800">
          AI 小说转剧本
        </Title>
        <Text className="text-gray-500 text-lg">
          上传小说文本，AI 自动分析并转换为结构化 YAML 剧本
        </Text>
      </div>

      {/* Feature cards */}
      <Row gutter={16} className="mb-8">
        {features.map((f) => (
          <Col key={f.title} span={8}>
            <Card
              className="text-center border-0 shadow-sm hover:shadow-md transition-shadow !rounded-xl h-full"
              styles={{ body: { padding: '24px 16px' } }}
            >
              <div className="text-3xl text-indigo-500 mb-3">{f.icon}</div>
              <Text strong className="block mb-1">{f.title}</Text>
              <Text type="secondary" className="text-sm">{f.desc}</Text>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Upload area */}
      <FileUploader onFileSelected={handleFileSelected} />

      {/* Settings */}
      <SettingsPanel settings={settings} onChange={onSettingsChange} />

      {/* CTA */}
      <div className="text-center mt-8 pb-16">
        <Button
          type="primary"
          size="large"
          icon={<RocketOutlined />}
          loading={loading}
          onClick={handleStart}
          className="!h-12 !px-10 !text-lg !rounded-xl !shadow-sm hover:!shadow-md !font-medium"
        >
          开始转换
        </Button>
      </div>
    </div>
  )
}

export default UploadPage
