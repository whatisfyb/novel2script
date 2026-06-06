import { Select, Space } from 'antd'
import { VideoCameraOutlined, SettingOutlined, GlobalOutlined } from '@ant-design/icons'
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
    <div
      className="mt-5 p-6"
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        boxShadow: 'var(--shadow-xs)',
      }}
    >
      <div className="flex items-center gap-2 mb-5">
        <SettingOutlined style={{ color: 'var(--accent-700)', fontSize: 15 }} />
        <span
          style={{
            fontWeight: 600,
            fontSize: 14,
            color: 'var(--ink-900)',
            letterSpacing: '0.01em',
          }}
        >
          转换设置
        </span>
        <span
          className="accent-dot ml-1"
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <VideoCameraOutlined style={{ color: 'var(--ink-300)', fontSize: 13 }} />
            <span
              style={{
                fontSize: 12,
                color: 'var(--ink-500)',
                fontWeight: 500,
                letterSpacing: '0.03em',
                textTransform: 'uppercase',
              }}
            >
              剧本类型
            </span>
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
                  <span style={{ fontSize: 12, color: 'var(--ink-500)' }}>{t.desc}</span>
                </Space>
              ),
            }))}
          />
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <GlobalOutlined style={{ color: 'var(--ink-300)', fontSize: 13 }} />
            <span
              style={{
                fontSize: 12,
                color: 'var(--ink-500)',
                fontWeight: 500,
                letterSpacing: '0.03em',
                textTransform: 'uppercase',
              }}
            >
              输出语言
            </span>
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
    </div>
  )
}

export default SettingsPanel
