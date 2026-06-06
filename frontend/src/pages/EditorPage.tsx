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
      <div
        className="px-6 py-3 flex-shrink-0 border-b"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border-color)',
        }}
      >
        <div className="flex justify-between items-center">
          <Space size="middle" align="center">
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={onReset}
              type="text"
              style={{ color: 'var(--ink-500)' }}
            >
              重新开始
            </Button>
            <div
              style={{ width: 1, height: 24, backgroundColor: 'var(--border-color)' }}
            />
            <Title
              level={5}
              style={{
                marginBottom: 0,
                color: 'var(--ink-700)',
                fontFamily: 'var(--font-display)',
              }}
            >
              剧本编辑器
            </Title>
            {file && (
              <Tag
                style={{
                  borderRadius: 4,
                  backgroundColor: 'var(--accent-100)',
                  color: 'var(--accent-700)',
                  border: 'none',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 11,
                }}
              >
                {file.name}
              </Tag>
            )}
          </Space>

          <Space align="center">
            {/* Status bar info */}
            <Tooltip title="行数 / 字符数">
              <Space size={4} style={{ color: 'var(--ink-500)', fontSize: 13 }}>
                <CodeOutlined />
                <span>{lineCount} 行</span>
                <span style={{ color: 'var(--ink-300)' }}>·</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>
                  {charCount.toLocaleString()} 字
                </span>
              </Space>
            </Tooltip>
            <div
              style={{ width: 1, height: 24, backgroundColor: 'var(--border-color)' }}
            />
            <ExportPanel yamlText={editedYaml} />
          </Space>
        </div>
      </div>

      {/* Editor + Preview */}
      <div className="flex-1 p-4 min-h-0 flex gap-4">
        {/* YAML Editor */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="flex items-center gap-2 mb-2 px-1 flex-shrink-0">
            <span className="accent-dot" />
            <Text
              style={{
                color: 'var(--ink-700)',
                fontWeight: 500,
                fontSize: 13,
                letterSpacing: '0.02em',
              }}
            >
              YAML 编辑器
            </Text>
          </div>
          <div
            className="flex-1 overflow-hidden border min-h-0"
            style={{
              borderRadius: 8,
              borderColor: 'var(--border-color)',
              boxShadow: 'var(--shadow-xs)',
              backgroundColor: '#fff',
            }}
          >
            <MonacoYaml value={editedYaml} onChange={setEditedYaml} />
          </div>
        </div>

        {/* Script Preview */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="flex items-center gap-2 mb-2 px-1 flex-shrink-0">
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: 'var(--accent-500)',
                display: 'inline-block',
              }}
            />
            <Text
              style={{
                color: 'var(--ink-700)',
                fontWeight: 500,
                fontSize: 13,
                letterSpacing: '0.02em',
              }}
            >
              剧本预览
            </Text>
          </div>
          <div
            className="flex-1 overflow-hidden border min-h-0"
            style={{
              borderRadius: 8,
              borderColor: 'var(--border-color)',
              boxShadow: 'var(--shadow-xs)',
            }}
          >
            <ScriptPreview yamlText={editedYaml} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default EditorPage
