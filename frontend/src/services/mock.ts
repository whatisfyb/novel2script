import type { ConversionProgress } from '@/types'

export const MOCK_YAML = `meta:
  title: "示例剧本"
  original_title: "示例小说"
  author: "测试作者"
  adapter: "AI"
  type: "tv"
  language: "zh"
  created_at: "2026-06-05T10:00:00Z"
  source_chapters: 3
  synopsis: "一个关于勇气与选择的故事。"
characters:
  - id: "lin_xiao"
    name: "林晓"
    aliases: ["晓晓"]
    role: "protagonist"
    description: "年轻的程序员，沉默寡言。"
    first_appearance: 1
  - id: "chen_yi"
    name: "陈一"
    role: "supporting"
    description: "林晓的同事，热情开朗。"
locations:
  - id: "office"
    name: "办公室"
    type: "indoor"
    description: "开放式办公区，几张桌子并在一起。"
acts:
  - id: "act_1"
    title: "第一幕：相遇"
    chapters: [1, 2]
    synopsis: "林晓和陈一在办公室相遇。"
    scenes:
      - id: "scene_001"
        act_id: "act_1"
        number: 1
        heading:
          location: "office"
          time: "day"
          type: "interior"
        description: "明亮的办公室，键盘敲击声此起彼伏。"
        beats:
          - id: "beat_001_01"
            type: "action"
            character: "lin_xiao"
            content: "林晓盯着屏幕，手指在键盘上飞舞。"
            emotion: "focused"
          - id: "beat_001_02"
            type: "dialogue"
            character: "chen_yi"
            parenthetical: "热情地"
            content: "嘿！新来的？我是陈一。"
            emotion: "cheerful"
          - id: "beat_001_03"
            type: "dialogue"
            character: "lin_xiao"
            parenthetical: "犹豫"
            content: "嗯...我是林晓。"
            emotion: "shy"
          - id: "beat_001_04"
            type: "transition"
            content: "CUT TO:"
        notes: "对应原书第1章 P1-P3"
`

export function simulateProgress(
  onUpdate: (progress: ConversionProgress) => void,
  onComplete: () => void,
): void {
  const stages = [
    { stage: 'parse', message: '正在解析文件...', percentage: 10 },
    { stage: 'split', message: '正在切分章节...', percentage: 20 },
    { stage: 'analyze', message: '正在分析角色和场景...', percentage: 35 },
    { stage: 'segment', message: '正在切分场景 (第 1 章/共 3 章)', percentage: 50, chapter: 1, total_chapters: 3 },
    { stage: 'segment', message: '正在切分场景 (第 2 章/共 3 章)', percentage: 60, chapter: 2, total_chapters: 3 },
    { stage: 'segment', message: '正在切分场景 (第 3 章/共 3 章)', percentage: 70, chapter: 3, total_chapters: 3 },
    { stage: 'extract', message: '正在提取对白和动作...', percentage: 85 },
    { stage: 'assemble', message: '正在组装 YAML...', percentage: 95 },
    { stage: 'done', message: '转换完成！', percentage: 100 },
  ]

  let index = 0
  const interval = setInterval(() => {
    if (index < stages.length) {
      onUpdate(stages[index])
      index++
    } else {
      clearInterval(interval)
      onComplete()
    }
  }, 800)
}
