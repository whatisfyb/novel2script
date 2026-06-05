import type { Screenplay, Scene, Beat } from '@/types'
import yaml from 'yaml'

export function exportAsYaml(screenplay: Screenplay): string {
  return yaml.stringify(screenplay, { sortMapEntries: false })
}

export function exportAsFountain(screenplay: Screenplay): string {
  const lines: string[] = []

  // Title page
  lines.push(`Title: ${screenplay.meta.title}`)
  lines.push(`Credit: ${screenplay.meta.adapter || 'Unknown'}`)
  lines.push(`Source: Based on "${screenplay.meta.original_title}" by ${screenplay.meta.author || 'Unknown'}`)
  lines.push('')

  for (const act of screenplay.acts) {
    lines.push(`# ${act.title}`)
    lines.push('')

    for (const scene of act.scenes) {
      lines.push(formatSceneHeading(scene))
      lines.push('')

      if (scene.description) {
        lines.push(scene.description)
        lines.push('')
      }

      for (const beat of scene.beats) {
        lines.push(formatBeat(beat, screenplay))
      }
    }
  }

  return lines.join('\n')
}

function formatSceneHeading(scene: Scene): string {
  const typeStr = scene.heading.type === 'interior' ? 'INT.' : 'EXT.'
  const locName = scene.heading.location.toUpperCase().replace(/_/g, ' ')
  const timeStr = scene.heading.time.toUpperCase()
  return `${typeStr} ${locName} - ${timeStr}`
}

function formatBeat(beat: Beat, screenplay: Screenplay): string {
  switch (beat.type) {
    case 'action':
      return `${beat.content}\n\n`

    case 'dialogue': {
      const char = screenplay.characters.find((c) => c.id === beat.character)
      const name = (char?.name || beat.character || 'UNKNOWN').toUpperCase()
      let result = `${name}\n`
      if (beat.parenthetical) {
        result += `(${beat.parenthetical})\n`
      }
      result += `${beat.content}\n\n`
      return result
    }

    case 'transition':
      return `> ${beat.content}\n\n`

    case 'voiceover': {
      const char = screenplay.characters.find((c) => c.id === beat.character)
      const name = (char?.name || 'NARRATOR').toUpperCase()
      return `${name} (V.O.)\n${beat.content}\n\n`
    }

    case 'montage':
      return `MONTAGE:\n${beat.content}\n\nEND MONTAGE\n\n`

    default:
      return `${beat.content}\n\n`
  }
}
