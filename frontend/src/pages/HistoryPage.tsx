import { useEffect, useState, useMemo } from 'react'
import { Button, Input, Select, Space, Typography, Popconfirm, message, Empty } from 'antd'
import {
  SearchOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileTextOutlined,
  CalendarOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import type { FC } from 'react'
import type { HistoryRecord, ScriptType, ConversionStatus } from '@/types'
import { fetchHistory, deleteHistoryRecord } from '@/services/history'
import { useSessionStore } from '@/stores/session'

const { Title, Text } = Typography

const STATUS_CONFIG: Record<ConversionStatus, { label: string; color: string; bg: string }> = {
  completed: { label: '已完成', color: 'var(--accent-700)', bg: 'var(--accent-100)' },
  processing: { label: '处理中', color: 'var(--ink-700)', bg: 'var(--ink-100)' },
  failed: { label: '失败', color: '#991b1b', bg: '#fee2e2' },
}

const SCRIPT_TYPE_LABELS: Record<ScriptType, string> = {
  movie: '电影',
  tv: '电视剧',
  short_video: '短剧',
  stage: '舞台剧',
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}.${month}.${day}`
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const day = 86400000
  if (diff < day) return '今天'
  if (diff < 2 * day) return '昨天'
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`
  if (diff < 30 * day) return `${Math.floor(diff / (7 * day))} 周前`
  return formatDate(iso)
}

const HistoryPage: FC = () => {
  const { loadHistoryYaml, setStep } = useSessionStore()
  const [records, setRecords] = useState<HistoryRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchHistory()
      setRecords(data)
    } finally {
      setLoading(false)
    }
  }

  const filtered = useMemo(() => {
    let result = records
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.filename.toLowerCase().includes(q),
      )
    }
    if (filterType !== 'all') {
      result = result.filter((r) => r.script_type === filterType)
    }
    return result.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
  }, [records, search, filterType])

  const handleDelete = async (id: string) => {
    await deleteHistoryRecord(id)
    setRecords((prev) => prev.filter((r) => r.id !== id))
    message.success('已删除')
  }

  const handleView = (record: HistoryRecord) => {
    if (record.status === 'failed' || !record.yaml) {
      message.warning('该记录无可用结果')
      return
    }
    loadHistoryYaml(record.yaml)
  }

  const handleBackToUpload = () => {
    setStep('upload')
  }

  return (
    <div
      className="max-w-6xl mx-auto px-6"
      style={{ minHeight: 'calc(100vh - 120px)' }}
    >
      {/* Header */}
      <div className="pt-12 pb-8 fade-up">
        <div className="flex items-baseline justify-between mb-2">
          <Title
            level={2}
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '2rem',
              fontWeight: 700,
              color: 'var(--ink-900)',
              marginBottom: 0,
              letterSpacing: '-0.02em',
            }}
          >
            历史<span style={{ color: 'var(--accent-700)' }}>记录</span>
          </Title>
          <Text style={{ fontSize: 13, color: 'var(--ink-500)' }}>
            共 {filtered.length} 条记录
          </Text>
        </div>
        <div
          style={{
            width: 48,
            height: 2,
            backgroundColor: 'var(--accent-700)',
            marginTop: 4,
            marginBottom: 8,
          }}
        />
        <Text style={{ color: 'var(--ink-500)', fontSize: 14 }}>
          查看和管理过往的小说转换记录
        </Text>
      </div>

      {/* Toolbar */}
      <div
        className="flex items-center justify-between gap-4 mb-6 fade-up fade-up-delay-1"
        style={{
          padding: '12px 16px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 8,
          boxShadow: 'var(--shadow-xs)',
        }}
      >
        <Space size="middle">
          <Input
            placeholder="搜索标题或文件名..."
            prefix={<SearchOutlined style={{ color: 'var(--ink-300)' }} />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            allowClear
            style={{ width: 280, height: 36 }}
          />
          <Select
            value={filterType}
            onChange={setFilterType}
            style={{ width: 120 }}
            size="middle"
            options={[
              { value: 'all', label: '全部类型' },
              { value: 'movie', label: '电影' },
              { value: 'tv', label: '电视剧' },
              { value: 'short_video', label: '短剧' },
              { value: 'stage', label: '舞台剧' },
            ]}
          />
        </Space>

        <Button.Group>
          <Button
            type={viewMode === 'card' ? 'primary' : 'default'}
            icon={<AppstoreOutlined />}
            onClick={() => setViewMode('card')}
            style={
              viewMode === 'card'
                ? { backgroundColor: 'var(--ink-900)', borderColor: 'var(--ink-900)' }
                : {}
            }
          />
          <Button
            type={viewMode === 'list' ? 'primary' : 'default'}
            icon={<UnorderedListOutlined />}
            onClick={() => setViewMode('list')}
            style={
              viewMode === 'list'
                ? { backgroundColor: 'var(--ink-900)', borderColor: 'var(--ink-900)' }
                : {}
            }
          />
        </Button.Group>
      </div>

      {/* Content */}
      {filtered.length === 0 && !loading ? (
        <div
          className="flex flex-col items-center justify-center fade-up fade-up-delay-2"
          style={{ padding: '80px 0' }}
        >
          <Empty
            description={
              <span style={{ color: 'var(--ink-500)' }}>
                {search || filterType !== 'all'
                  ? '没有匹配的记录'
                  : '暂无历史记录，开始你的第一次转换吧'}
              </span>
            }
          />
          {!search && filterType === 'all' && (
            <Button
              type="primary"
              onClick={handleBackToUpload}
              style={{
                marginTop: 24,
                backgroundColor: 'var(--ink-900)',
                borderColor: 'var(--ink-900)',
              }}
            >
              开始转换
            </Button>
          )}
        </div>
      ) : viewMode === 'card' ? (
        /* Card Grid */
        <div
          className="grid gap-4 fade-up fade-up-delay-2"
          style={{
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          }}
        >
          {filtered.map((record) => (
            <HistoryCard
              key={record.id}
              record={record}
              onView={handleView}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : (
        /* List View */
        <div
          className="fade-up fade-up-delay-2"
          style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            boxShadow: 'var(--shadow-xs)',
            overflow: 'hidden',
          }}
        >
          {filtered.map((record, idx) => (
            <HistoryListItem
              key={record.id}
              record={record}
              onView={handleView}
              onDelete={handleDelete}
              isLast={idx === filtered.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/* ── Card View ── */

interface CardProps {
  record: HistoryRecord
  onView: (r: HistoryRecord) => void
  onDelete: (id: string) => void
}

const HistoryCard: FC<CardProps> = ({ record, onView, onDelete }) => {
  const status = STATUS_CONFIG[record.status]

  return (
    <div
      className="surface-card p-5 flex flex-col"
      style={{ borderRadius: 8, minHeight: 200 }}
    >
      {/* Top: status + type */}
      <div className="flex items-center justify-between mb-3">
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 11,
            fontWeight: 600,
            padding: '3px 8px',
            borderRadius: 3,
            letterSpacing: '0.03em',
            color: status.color,
            backgroundColor: status.bg,
          }}
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              backgroundColor: status.color,
            }}
          />
          {status.label}
        </span>
        <Text
          style={{
            fontSize: 12,
            color: 'var(--ink-500)',
          }}
        >
          {SCRIPT_TYPE_LABELS[record.script_type]}
        </Text>
      </div>

      {/* Title */}
      <Text
        strong
        style={{
          display: 'block',
          fontSize: 17,
          fontFamily: 'var(--font-display)',
          color: 'var(--ink-900)',
          marginBottom: 4,
          lineHeight: 1.3,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {record.title}
      </Text>

      {/* Filename */}
      <Text
        style={{
          fontSize: 12,
          color: 'var(--ink-500)',
          fontFamily: 'var(--font-mono)',
          marginBottom: 12,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        <FileTextOutlined style={{ marginRight: 4 }} />
        {record.filename}
      </Text>

      {/* Stats */}
      <div className="flex gap-4 mb-4 flex-1">
        <Stat label="章节" value={record.chapters} />
        <Stat label="场景" value={record.scenes} />
        <Stat label="人物" value={record.characters} />
      </div>

      {/* Bottom: date + actions */}
      <div
        className="flex items-center justify-between pt-3"
        style={{ borderTop: '1px solid var(--border-color)' }}
      >
        <Text
          style={{
            fontSize: 12,
            color: 'var(--ink-500)',
          }}
        >
          <CalendarOutlined style={{ marginRight: 4 }} />
          {timeAgo(record.created_at)}
        </Text>
        <Space size="small">
          <Button
            size="small"
            type="text"
            icon={<EyeOutlined />}
            onClick={() => onView(record)}
            style={{ color: 'var(--accent-700)' }}
          >
            查看
          </Button>
          <Popconfirm
            title="确定删除这条记录吗？"
            description="删除后不可恢复"
            onConfirm={() => onDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              size="small"
              type="text"
              icon={<DeleteOutlined />}
              style={{ color: 'var(--ink-500)' }}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      </div>
    </div>
  )
}

/* ── List Item ── */

interface ListItemProps {
  record: HistoryRecord
  onView: (r: HistoryRecord) => void
  onDelete: (id: string) => void
  isLast: boolean
}

const HistoryListItem: FC<ListItemProps> = ({ record, onView, onDelete, isLast }) => {
  const status = STATUS_CONFIG[record.status]

  return (
    <div
      className="flex items-center justify-between px-5 py-4 transition-colors"
      style={{
        borderBottom: isLast ? 'none' : '1px solid var(--border-color)',
        cursor: 'pointer',
      }}
      onClick={() => onView(record)}
    >
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 6,
            backgroundColor: 'var(--bg-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <FileTextOutlined style={{ color: 'var(--accent-700)', fontSize: 16 }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Text
              strong
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 15,
                color: 'var(--ink-900)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {record.title}
            </Text>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 10,
                fontWeight: 600,
                padding: '2px 6px',
                borderRadius: 3,
                color: status.color,
                backgroundColor: status.bg,
              }}
            >
              {status.label}
            </span>
          </div>
          <Text
            style={{
              fontSize: 12,
              color: 'var(--ink-500)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {record.filename} · {SCRIPT_TYPE_LABELS[record.script_type]} · {record.chapters}章 · {record.scenes}场
          </Text>
        </div>
      </div>

      <div className="flex items-center gap-3 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
        <Text style={{ fontSize: 12, color: 'var(--ink-500)' }}>
          {timeAgo(record.created_at)}
        </Text>
        <Button
          size="small"
          type="text"
          icon={<EyeOutlined />}
          onClick={() => onView(record)}
          style={{ color: 'var(--accent-700)' }}
        />
        <Popconfirm
          title="确定删除？"
          onConfirm={() => onDelete(record.id)}
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button
            size="small"
            type="text"
            icon={<DeleteOutlined />}
            style={{ color: 'var(--ink-500)' }}
          />
        </Popconfirm>
      </div>
    </div>
  )
}

/* ── Stat ── */

const Stat: FC<{ label: string; value: number }> = ({ label, value }) => (
  <div>
    <div
      style={{
        fontFamily: 'var(--font-display)',
        fontSize: 20,
        fontWeight: 700,
        color: 'var(--ink-900)',
        lineHeight: 1,
      }}
    >
      {value}
    </div>
    <div
      style={{
        fontSize: 11,
        color: 'var(--ink-500)',
        marginTop: 2,
        letterSpacing: '0.03em',
      }}
    >
      {label}
    </div>
  </div>
)

export default HistoryPage
