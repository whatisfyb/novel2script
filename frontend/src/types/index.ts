export type ScriptType = 'movie' | 'tv' | 'short_video' | 'stage'
export type Language = 'zh' | 'en' | 'bilingual'
export type CharacterRole = 'protagonist' | 'supporting' | 'antagonist' | 'extra'
export type LocationType = 'indoor' | 'outdoor' | 'mixed' | 'virtual'
export type SceneTime = 'day' | 'night' | 'dawn' | 'dusk' | 'continuous'
export type SceneType = 'interior' | 'exterior'
export type BeatType = 'action' | 'dialogue' | 'transition' | 'voiceover' | 'montage'

export interface ScreenplayMeta {
  title: string
  original_title?: string
  author?: string
  adapter?: string
  type: ScriptType
  language: Language
  created_at: string
  source_chapters: number
  synopsis?: string
}

export interface Character {
  id: string
  name: string
  aliases?: string[]
  role: CharacterRole
  description?: string
  first_appearance?: number
}

export interface Location {
  id: string
  name: string
  type: LocationType
  description?: string
}

export interface Beat {
  id: string
  type: BeatType
  character?: string | null
  content: string
  parenthetical?: string | null
  emotion?: string | null
  // short_video specific
  shot_type?: string
  duration?: string
  text_overlay?: string | null
  // stage specific
  blocking?: string
  lighting?: string
  props?: string[]
}

export interface Scene {
  id: string
  act_id: string
  number: number
  heading: {
    location: string
    time: SceneTime
    type: SceneType
  }
  description: string
  beats: Beat[]
  notes?: string
}

export interface Act {
  id: string
  title: string
  chapters?: number[]
  synopsis?: string
  scenes: Scene[]
}

export interface Screenplay {
  meta: ScreenplayMeta
  characters: Character[]
  locations: Location[]
  acts: Act[]
}

// API types
export interface ConversionProgress {
  stage: string
  chapter?: number
  total_chapters?: number
  message: string
  percentage: number
}

export interface UploadResponse {
  session_id: string
  filename: string
  chapters_detected?: number
}

export interface ConversionSettings {
  title?: string
  author?: string
  script_type?: ScriptType
  language?: Language
  model?: string
}

// Auth types
export interface User {
  id: string
  username: string
  email?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface AuthResponse {
  token: string
  user: User
}
