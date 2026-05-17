// ─────────────────────────────────────────────────────────
// api/types.ts
// TypeScript types matching the actual FastAPI/Pydantic
// response shapes. Derived from reading the backend routes.
// ─────────────────────────────────────────────────────────

// ── GET /seasons ──────────────────────────────────────────

export interface Season {
  season: number
  race_count: number
  computed_race_count: number
}

// ── GET /seasons/{season}/races ───────────────────────────

export interface Race {
  id: string            // uuid — used as session_id in other endpoints
  season: number
  round: number
  circuit_key: string
  circuit_name: string
  race_date: string     // ISO date string
  computed_at: string | null
}

// ── Shared types ──────────────────────────────────────────

export type StrategyType = 'proactive' | 'reactive' | 'neutral'
export type RaceFlag     = 'green' | 'yellow' | 'sc' | 'vsc' | 'red'

// ── GET /races/{session_id}/pit-stops ─────────────────────
// Full detail — includes all UTS inputs

export interface PitStopDetail {
  id: string
  session_id: string
  driver_code: string
  team: string
  lap: number
  tire_age_self: number
  compound_self: string
  gap_behind: number | null
  tire_age_behind: number
  compound_behind: string
  ptl: number | null
  ppd: number | null
  uts: number | null
  strategy_type: StrategyType
  pit_loss_used: number
  race_flag: RaceFlag
  is_opportunistic: boolean
}

// ── GET /races/{session_id}/timeline ─────────────────────
// Lightweight — only fields needed for D3 rendering.

export interface TimelinePitEvent {
  id: string
  driver_code: string
  team: string
  lap: number
  uts: number | null
  strategy_type: StrategyType
  ptl: number | null
  ppd: number | null
  gap_behind: number | null
  compound_self: string | null
  race_flag: RaceFlag
  is_opportunistic: boolean
}

export interface RaceTimeline {
  session_id: string
  circuit_name: string
  season: number
  round: number
  race_date: string
  pit_events: TimelinePitEvent[]
}

// ── Derived: pit event merged with full detail ────────────

export interface MergedPitStop {
  id: string
  driver_code: string
  team: string
  lap: number
  uts: number | null
  strategy_type: StrategyType
  ptl: number | null
  ppd: number | null
  gap_behind: number | null
  compound_self: string | null
  race_flag: RaceFlag
  is_opportunistic: boolean

  session_id?: string
  tire_age_self?: number
  tire_age_behind?: number
  compound_behind?: string
  pit_loss_used?: number
}

// ── Derived: drivers grouped from flat pit_events ─────────

export interface DriverRow {
  driver_code: string
  team: string
  pit_stops: MergedPitStop[]
}

// ── GET /teams ────────────────────────────────────────────

export interface TeamList {
  teams: string[]
  season: number | null
}

// ── GET /teams/{team}/strategy-profile ───────────────────
// Season is an optional query param; response always contains
// a `seasons` array (one entry per season with data).

export interface TeamSeasonStats {
  season: number
  avg_uts: number | null
  reactive_stop_rate: number   // 0–100 (percentage, not fraction)
  total_green_stops: number
  proactive_stops: number
  reactive_stops: number
  neutral_stops: number
  opportunistic_stops: number
}

export interface TeamStrategyProfile {
  team: string
  seasons: TeamSeasonStats[]
  best_stop: PitStopDetail | null
  worst_stop: PitStopDetail | null
}

// ── GET /circuits/{circuit_key}/analysis ─────────────────

export interface CircuitAnalysis {
  circuit_key: string
  circuit_name: string | null
  circuit_type: 'street' | 'permanent' | 'hybrid' | null
  pit_loss_estimate: number | null
  sc_loss_factor: number | null
  total_green_stops: number
  total_sc_stops: number
  avg_uts: number | null
  negative_uts_pct: number      // 0–100 (percentage of stops below midpoint)
  avg_gap_behind_at_pit: number | null
  avg_ppd: number | null
}

// ── GET /insights/undercut-ranking ───────────────────────

export interface RankedStop {
  rank: number
  stop: PitStopDetail
  circuit_name: string
  season: number
  round: number
}

export interface UndercutRanking {
  best: RankedStop[]
  worst: RankedStop[]
}