// ─────────────────────────────────────────────────────────
// store/uiStore.ts
// Global UI state. Selections are also mirrored to URL
// search params in TimelineView for shareability.
// ─────────────────────────────────────────────────────────

import { create } from 'zustand'

interface UiState {
  selectedSeason: number | null
  selectedSessionId: string | null

  setSeason: (season: number | null) => void
  setSessionId: (sessionId: string | null) => void
}

const useUiStore = create<UiState>((set) => ({
  selectedSeason: null,
  selectedSessionId: null,

  setSeason: (season) =>
    set({ selectedSeason: season, selectedSessionId: null }),

  setSessionId: (sessionId) =>
    set({ selectedSessionId: sessionId }),
}))

export default useUiStore