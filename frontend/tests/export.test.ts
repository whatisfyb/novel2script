import { describe, it, expect } from 'vitest'
import { exportAsFountain } from '@/services/export'
import type { Screenplay } from '@/types'

const mockScreenplay: Screenplay = {
  meta: {
    title: 'Test Movie',
    original_title: 'Test',
    author: 'Author',
    adapter: 'AI',
    type: 'movie',
    language: 'zh',
    created_at: '2026-06-05T10:00:00Z',
    source_chapters: 1,
  },
  characters: [
    { id: 'alice', name: 'Alice', role: 'protagonist' },
  ],
  locations: [
    { id: 'room', name: 'Room', type: 'indoor' },
  ],
  acts: [
    {
      id: 'act1',
      title: 'Act 1',
      scenes: [
        {
          id: 's1',
          act_id: 'act1',
          number: 1,
          heading: { location: 'room', time: 'day', type: 'interior' },
          description: 'A simple room.',
          beats: [
            { id: 'b1', type: 'action', content: 'Alice enters.' },
            { id: 'b2', type: 'dialogue', character: 'alice', content: 'Hello world.', parenthetical: 'softly' },
            { id: 'b3', type: 'transition', content: 'CUT TO:' },
          ],
        },
      ],
    },
  ],
}

describe('Export Service', () => {
  it('should export to Fountain format', () => {
    const fountain = exportAsFountain(mockScreenplay)
    expect(fountain).toContain('Title: Test Movie')
    expect(fountain).toContain('INT.')
    expect(fountain).toContain('ALICE')
    expect(fountain).toContain('Hello world.')
    expect(fountain).toContain('CUT TO:')
  })
})
