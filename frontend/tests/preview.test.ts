import { describe, it, expect } from 'vitest'
import { parseScreenplayForPreview } from '@/components/ScriptPreview'

describe('ScriptPreview parser', () => {
  it('should parse YAML into screenplay', () => {
    const yamlText = `
meta:
  title: "Test"
  type: "movie"
  language: "zh"
  created_at: "2026-01-01T00:00:00Z"
  source_chapters: 1
characters:
  - id: "alice"
    name: "Alice"
    role: "protagonist"
locations:
  - id: "room"
    name: "Room"
    type: "indoor"
acts:
  - id: "act1"
    title: "Act 1"
    scenes:
      - id: "s1"
        act_id: "act1"
        number: 1
        heading:
          location: "room"
          time: "day"
          type: "interior"
        description: "A room."
        beats:
          - id: "b1"
            type: "dialogue"
            character: "alice"
            content: "Hello"
`
    const result = parseScreenplayForPreview(yamlText)
    expect(result).not.toBeNull()
    expect(result!.meta.title).toBe('Test')
    expect(result!.characters).toHaveLength(1)
    expect(result!.acts[0].scenes[0].beats).toHaveLength(1)
  })

  it('should return null for invalid YAML', () => {
    const result = parseScreenplayForPreview('{{{invalid yaml')
    expect(result).toBeNull()
  })
})
