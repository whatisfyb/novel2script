import { Select, Card, Space, Tag } from 'antd'
import { VideoCameraOutlined, SettingOutlined } from '@ant-design/icons'
import type { FC } from 'react'
import type { ConversionSettings, ScriptType, Language } from '@/types'

interface Props {
  settings: ConversionSettings
  onChange: (settings: ConversionSettings) => void
}

const SCRIPT_TYPES: { value: ScriptType; label: string; desc: string }[] = [
  { value: 'tv', label: '电视剧', desc: '多幕多集' },
  { value: 'movie', label: '电影', desc: '三幕结构' },
  { value: 'short_video', label: '短剧/短视频', desc: '快节奏' },
  { value: 'stage', label: '舞台剧', desc: '场景调度' },
]

const LANGUAGES: { value: Language; label: string }[] = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
  { value: 'bilingual', label: '中英双语' },
]

const SettingsPanel: FC<Props> = ({ settings, onChange }) => {
  return (
    <Card
      className="!rounded-2xl !border-0 !shadow-sm mt-4"
      title={
        <Space>
          <SettingOutlined className="text-indigo-500" />
          <span>转换设置</span>
        </Space>
      }
      styles={{ body: { padding: '20px 24px' } }}
    >
      <div className="grid grid-cols-2 gap-6">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <VideoCameraOutlined className="text-gray-400" />
            <span className="text-sm text-gray-600 font-medium">剧本类型</span>
          </div>
          <Select
            value={settings.script_type}
            onChange={(v) => onChange({ ...settings, script_type: v })}
            className="w-full"
            size="large"
            options={SCRIPT_TYPES.map((t) => ({
              value: t.value,
              label: (
                <Space>
                  {t.label}
                  <Tag className="text-xs" color="default">{t.desc}</Tag>
                </Space>
              ),
            }))}
          />
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm text-gray-400">🌐</span>
            <span className="text-sm text-gray-600 font-medium">输出语言</span>
          </div>
          <Select
            value={settings.language || 'zh'}
            onChange={(v) => onChange({ ...settings, language: v })}
            className="w-full"
            size="large"
            options={LANGUAGES.map((l) => ({
              value: l.value,
              label: l.label,
            }))}
          />
        </div>
      </div>
    </Card>
  )
}

export default SettingsPanel
