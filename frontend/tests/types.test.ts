import { describe, it, expect } from 'vitest'
import type {
  Screenplay, ScreenplayMeta, Character, Location,
  Act, Scene, Beat, BeatType, ScriptType
} from '@/types'

describe('Type definitions', () => {
  it('should create a valid Screenplay shape', () => {
    const screenplay: Screenplay = {
      meta: {
        title: 'Test',
        original_title: 'Test',
        author: 'Author',
        adapter: 'AI',
        type: 'movie',
        language: 'zh',
        created_at: '2026-06-05T10:00:00Z',
        source_chapters: 3,
        synopsis: 'A test story.',
      },
      characters: [],
      locations: [],
      acts: [],
    }
    expect(screenplay.meta.title).toBe('Test')
  })

  it('should accept all BeatType values', () => {
    const types: BeatType[] = ['action', 'dialogue', 'transition', 'voiceover', 'montage']
    expect(types).toHaveLength(5)
  })

  it('should accept all ScriptType values', () => {
    const types: ScriptType[] = ['movie', 'tv', 'short_video', 'stage']
    expect(types).toHaveLength(4)
  })
})
