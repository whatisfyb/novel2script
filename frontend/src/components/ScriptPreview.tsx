import { useMemo } from 'react'
import { Typography, Empty } from 'antd'
import type { FC } from 'react'
import yaml from 'yaml'
import type { Screenplay, Scene, Beat } from '@/types'

const { Title, Paragraph } = Typography

// Exported for testing
export function parseScreenplayForPreview(yamlText: string): Screenplay | null {
  try {
    const parsed = yaml.parse(yamlText) as Screenplay
    if (!parsed.meta || !parsed.acts) return null
    return parsed
  } catch {
    return null
  }
}

interface Props {
  yamlText: string
}

const ScriptPreview: FC<Props> = ({ yamlText }) => {
  const screenplay = useMemo(() => parseScreenplayForPreview(yamlText), [yamlText])

  if (!screenplay) {
    return <Empty description="YAML 格式错误，无法预览" />
  }

  const charMap = new Map(screenplay.characters.map((c) => [c.id, c.name]))

  return (
    <div className="h-full overflow-y-auto p-6 bg-gray-50/80">
      <Title level={3}>{screenplay.meta.title}</Title>
      <Paragraph type="secondary">{screenplay.meta.synopsis}</Paragraph>

      {screenplay.acts.map((act) => (
        <div key={act.id} className="mb-8">
          <Title level={4} className="border-b pb-2 mb-4">{act.title}</Title>

          {act.scenes.map((scene) => (
            <SceneRenderer key={scene.id} scene={scene} charMap={charMap} />
          ))}
        </div>
      ))}
    </div>
  )
}

const SceneRenderer: FC<{ scene: Scene; charMap: Map<string, string> }> = ({ scene, charMap }) => {
  return (
    <div className="mb-6 bg-white p-4 rounded shadow-sm">
      <div className="font-bold text-sm mb-2">
        {scene.heading.type === 'interior' ? '内景' : '外景'} · {charMap.get(scene.heading.location) || scene.heading.location} · {timeLabel(scene.heading.time)}
      </div>
      {scene.description && (
        <Paragraph className="text-gray-600 italic">{scene.description}</Paragraph>
      )}
      <div className="space-y-2">
        {scene.beats.map((beat) => (
          <BeatRenderer key={beat.id} beat={beat} charMap={charMap} />
        ))}
      </div>
    </div>
  )
}

const BeatRenderer: FC<{ beat: Beat; charMap: Map<string, string> }> = ({ beat, charMap }) => {
  switch (beat.type) {
    case 'action':
      return <div className="text-gray-800">{beat.content}</div>

    case 'dialogue':
      return (
        <div className="pl-8">
          <div className="font-bold text-center">{charMap.get(beat.character || '') || beat.character}</div>
          {beat.parenthetical && <div className="text-center text-gray-500 italic">({beat.parenthetical})</div>}
          <div className="text-center">{beat.content}</div>
        </div>
      )

    case 'transition':
      return <div className="text-right font-bold text-gray-700">{beat.content}</div>

    case 'voiceover':
      return (
        <div className="pl-8 text-gray-700">
          <div className="font-bold">{charMap.get(beat.character || '') || '旁白'} (画外音)</div>
          <div className="italic">{beat.content}</div>
        </div>
      )

    default:
      return <div className="text-gray-600">{beat.content}</div>
  }
}

function timeLabel(time: string): string {
  const labels: Record<string, string> = { day: '日', night: '夜', dawn: '清晨', dusk: '黄昏', continuous: '连续' }
  return labels[time] || time
}

export default ScriptPreview
