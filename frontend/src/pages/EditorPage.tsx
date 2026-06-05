import { useState } from 'react'
import { Typography, Button, Space, Tag, Tooltip } from 'antd'
import {
  ArrowLeftOutlined, CodeOutlined,
} from '@ant-design/icons'
import type { FC } from 'react'
import MonacoYaml from '@/components/MonacoYaml'
import ScriptPreview from '@/components/ScriptPreview'
import ExportPanel from '@/components/ExportPanel'
import { useSessionStore } from '@/stores/session'

const { Title, Text } = Typography

interface Props {
  onReset: () => void
}

const EditorPage: FC<Props> = ({ onReset }) => {
  const { yaml: storedYaml, file } = useSessionStore()
  const [editedYaml, setEditedYaml] = useState(storedYaml || '')
  const lineCount = editedYaml.split('\n').length
  const charCount = editedYaml.length

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 64px)' }}>
      {/* Toolbar */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0">
        <div className="flex justify-between items-center">
          <Space size="middle">
            <Button icon={<ArrowLeftOutlined />} onClick={onReset} type="text" className="text-gray-500">
              重新开始
            </Button>
            <div className="w-px h-6 bg-gray-200" />
            <Title level={5} className="!mb-0 !text-gray-700">剧本编辑器</Title>
            {file && (
              <Tag color="purple" className="!rounded-full">{file.name}</Tag>
            )}
          </Space>

          <Space>
            {/* Status bar info */}
            <Tooltip title="行数 / 字符数">
              <Space size={4} className="text-gray-400 text-sm">
                <CodeOutlined />
                <span>{lineCount} 行</span>
                <span className="text-gray-300">·</span>
                <span>{charCount.toLocaleString()} 字</span>
              </Space>
            </Tooltip>
            <div className="w-px h-6 bg-gray-200" />
            <ExportPanel yamlText={editedYaml} />
          </Space>
        </div>
      </div>

      {/* Editor + Preview */}
      <div className="flex-1 p-4 min-h-0 flex gap-4">
        {/* YAML Editor */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="flex items-center gap-2 mb-2 px-1 flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-indigo-500" />
            <Text className="text-gray-600 font-medium text-sm">YAML 编辑器</Text>
          </div>
          <div className="flex-1 rounded-xl overflow-hidden border border-gray-200 shadow-sm bg-white min-h-0">
            <MonacoYaml value={editedYaml} onChange={setEditedYaml} />
          </div>
        </div>

        {/* Script Preview */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="flex items-center gap-2 mb-2 px-1 flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <Text className="text-gray-600 font-medium text-sm">剧本预览</Text>
          </div>
          <div className="flex-1 rounded-xl overflow-hidden border border-gray-200 shadow-sm min-h-0">
            <ScriptPreview yamlText={editedYaml} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default EditorPage
