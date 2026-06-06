import type { HistoryRecord } from '@/types'

/**
 * Mock history data — replace with real API calls when backend is ready.
 */

const MOCK_YAML_SAMPLE = `meta:
  title: 示例剧本
  type: tv
  language: zh
  created_at: "2025-06-01"
  source_chapters: 3
  synopsis: 一个关于梦想与现实的故事
characters:
  - id: char_001
    name: 林晨
    role: protagonist
    description: 28岁，怀揣编剧梦想的年轻人
locations:
  - id: loc_001
    name: 咖啡馆
    type: indoor
acts:
  - id: act_001
    title: 第一幕
    scenes:
      - id: scn_001
        number: 1
        heading:
          location: loc_001
          time: day
          type: interior
        description: 午后的阳光透过玻璃窗
        beats:
          - id: beat_001
            type: action
            content: 林晨坐在角落，翻看笔记本
          - id: beat_002
            type: dialogue
            character: char_001
            content: 这就是我想要的故事
`

const now = Date.now()
const day = 86400000

export const MOCK_HISTORY: HistoryRecord[] = [
  {
    id: 'rec_001',
    filename: '追风筝的人.txt',
    title: '追风筝的人',
    script_type: 'movie',
    language: 'zh',
    status: 'completed',
    created_at: new Date(now - 1 * day).toISOString(),
    chapters: 12,
    acts: 3,
    scenes: 28,
    characters: 8,
    yaml: MOCK_YAML_SAMPLE,
  },
  {
    id: 'rec_002',
    filename: '三体-黑暗森林.md',
    title: '黑暗森林',
    script_type: 'tv',
    language: 'zh',
    status: 'completed',
    created_at: new Date(now - 3 * day).toISOString(),
    chapters: 24,
    acts: 5,
    scenes: 62,
    characters: 15,
    yaml: MOCK_YAML_SAMPLE,
  },
  {
    id: 'rec_003',
    filename: '百年孤独.docx',
    title: '百年孤独',
    script_type: 'movie',
    language: 'bilingual',
    status: 'completed',
    created_at: new Date(now - 7 * day).toISOString(),
    chapters: 20,
    acts: 3,
    scenes: 45,
    characters: 22,
    yaml: MOCK_YAML_SAMPLE,
  },
  {
    id: 'rec_004',
    filename: '短剧-逆袭人生.txt',
    title: '逆袭人生',
    script_type: 'short_video',
    language: 'zh',
    status: 'completed',
    created_at: new Date(now - 14 * day).toISOString(),
    chapters: 5,
    acts: 3,
    scenes: 15,
    characters: 4,
    yaml: MOCK_YAML_SAMPLE,
  },
  {
    id: 'rec_005',
    filename: '茶馆-话剧版.md',
    title: '茶馆',
    script_type: 'stage',
    language: 'zh',
    status: 'failed',
    created_at: new Date(now - 21 * day).toISOString(),
    chapters: 3,
    acts: 0,
    scenes: 0,
    characters: 0,
    yaml: '',
  },
  {
    id: 'rec_006',
    filename: '流浪地球2.txt',
    title: '流浪地球 II',
    script_type: 'movie',
    language: 'zh',
    status: 'completed',
    created_at: new Date(now - 30 * day).toISOString(),
    chapters: 18,
    acts: 4,
    scenes: 36,
    characters: 12,
    yaml: MOCK_YAML_SAMPLE,
  },
  {
    id: 'rec_007',
    filename: 'sample-novel.docx',
    title: '示例小说',
    script_type: 'tv',
    language: 'zh',
    status: 'completed',
    created_at: new Date(now - 45 * day).toISOString(),
    chapters: 8,
    acts: 3,
    scenes: 20,
    characters: 6,
    yaml: MOCK_YAML_SAMPLE,
  },
  {
    id: 'rec_008',
    filename: '新春贺岁短剧.txt',
    title: '新春贺岁',
    script_type: 'short_video',
    language: 'zh',
    status: 'completed',
    created_at: new Date(now - 60 * day).toISOString(),
    chapters: 3,
    acts: 3,
    scenes: 9,
    characters: 5,
    yaml: MOCK_YAML_SAMPLE,
  },
]

/** Simulate async fetch */
export async function fetchHistory(): Promise<HistoryRecord[]> {
  await new Promise((r) => setTimeout(r, 300))
  return [...MOCK_HISTORY]
}

/** Simulate async delete */
export async function deleteHistoryRecord(id: string): Promise<void> {
  await new Promise((r) => setTimeout(r, 200))
  const idx = MOCK_HISTORY.findIndex((r) => r.id === id)
  if (idx >= 0) MOCK_HISTORY.splice(idx, 1)
}
