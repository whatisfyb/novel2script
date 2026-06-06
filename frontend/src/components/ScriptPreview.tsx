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
    return (
      <div className="h-full flex items-center justify-center" style={{ backgroundColor: 'var(--bg-subtle)' }}>
        <Empty description="YAML 格式错误，无法预览" />
      </div>
    )
  }

  const charMap = new Map(screenplay.characters.map((c) => [c.id, c.name]))

  return (
    <div
      className="h-full overflow-y-auto"
      style={{
        padding: '32px 40px',
        backgroundColor: 'var(--bg-subtle)',
        fontFamily: 'var(--font-body)',
      }}
    >
      {/* Title block — screenplay style */}
      <div className="text-center mb-8">
        <Title
          level={3}
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 700,
            color: 'var(--ink-900)',
            marginBottom: 4,
          }}
        >
          {screenplay.meta.title}
        </Title>
        <Paragraph
          style={{
            color: 'var(--ink-500)',
            fontSize: 13,
            fontStyle: 'italic',
            marginBottom: 0,
          }}
        >
          {screenplay.meta.synopsis}
        </Paragraph>
      </div>

      {screenplay.acts.map((act) => (
        <div key={act.id} className="mb-10">
          <div className="flex items-center gap-3 mb-5">
            <span
              style={{
                width: 24,
                height: 1,
                backgroundColor: 'var(--accent-700)',
              }}
            />
            <Title
              level={4}
              style={{
                fontFamily: 'var(--font-display)',
                color: 'var(--ink-900)',
                marginBottom: 0,
                fontWeight: 600,
              }}
            >
              {act.title}
            </Title>
          </div>

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
    <div
      className="mb-5 p-5"
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: 6,
      }}
    >
      {/* Scene heading — screenplay style */}
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: 'var(--ink-900)',
          marginBottom: 8,
        }}
      >
        {scene.heading.type === 'interior' ? 'INT.' : 'EXT.'} {charMap.get(scene.heading.location) || scene.heading.location} — {timeLabel(scene.heading.time)}
      </div>
      {scene.description && (
        <Paragraph
          style={{
            color: 'var(--ink-500)',
            fontStyle: 'italic',
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          {scene.description}
        </Paragraph>
      )}
      <div className="space-y-2.5">
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
      return (
        <div style={{ color: 'var(--ink-800)', fontSize: 14, lineHeight: 1.7 }}>
          {beat.content}
        </div>
      )

    case 'dialogue':
      return (
        <div style={{ paddingLeft: 48, paddingRight: 48, textAlign: 'center' }}>
          <div
            style={{
              fontWeight: 700,
              fontSize: 13,
              color: 'var(--ink-900)',
              marginBottom: 2,
            }}
          >
            {charMap.get(beat.character || '') || beat.character}
          </div>
          {beat.parenthetical && (
            <div
              style={{
                fontSize: 12,
                color: 'var(--ink-500)',
                fontStyle: 'italic',
              }}
            >
              ({beat.parenthetical})
            </div>
          )}
          <div style={{ fontSize: 14, color: 'var(--ink-800)' }}>
            {beat.content}
          </div>
        </div>
      )

    case 'transition':
      return (
        <div
          style={{
            textAlign: 'right',
            fontWeight: 700,
            fontSize: 12,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--ink-700)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {beat.content}
        </div>
      )

    case 'voiceover':
      return (
        <div style={{ paddingLeft: 48, paddingRight: 48 }}>
          <div
            style={{
              fontWeight: 700,
              fontSize: 13,
              color: 'var(--ink-900)',
              marginBottom: 2,
            }}
          >
            {charMap.get(beat.character || '') || '旁白'} (O.S.)
          </div>
          <div style={{ fontSize: 14, color: 'var(--ink-700)', fontStyle: 'italic' }}>
            {beat.content}
          </div>
        </div>
      )

    default:
      return <div style={{ color: 'var(--ink-600)', fontSize: 14 }}>{beat.content}</div>
  }
}

function timeLabel(time: string): string {
  const labels: Record<string, string> = { day: 'DAY', night: 'NIGHT', dawn: 'DAWN', dusk: 'DUSK', continuous: 'CONTINUOUS' }
  return labels[time] || time.toUpperCase()
}

export default ScriptPreview
