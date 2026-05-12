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

// ── GET /races/{session_id}/pit-stops ────────────────────
// Full detail — includes all UTS inputs

export interface PitStopDetail {
  id: string
  session_id: string
  driver_code: string
  team: string
  lap: number
  tire_age_self: number
  compound_self: string
  gap_behind: number
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
// Full detail lives in /pit-stops; TimelineView merges both.

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
// Concrete interface — avoids TypeScript spread inference issues.
// Required fields are always present (from /timeline).
// Optional fields appear after /pit-stops resolves and merges in.

export interface MergedPitStop {
  // Always present (from TimelinePitEvent)
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

  // Present after /pit-stops merges in
  session_id?: string
  tire_age_self?: number
  tire_age_behind?: number
  compound_behind?: string
  pit_loss_used?: number
}

// ── Derived: drivers grouped from flat pit_events ─────────
// Built client-side from RaceTimeline for the D3 component

export interface DriverRow {
  driver_code: string
  team: string
  pit_stops: MergedPitStop[]
}

// ── Team profile ──────────────────────────────────────
export interface TeamRaceUts {
  session_id: string;
  circuit_name: string;
  round: number;
  avg_uts: number;
  stop_count: number;
}

export interface TeamStrategyProfile {
  team: string;
  season: number;
  avg_uts: number;
  reactive_stop_rate: number;    // 0–1
  proactive_stop_rate: number;
  neutral_stop_rate: number;
  pit_lag_index: number;         // median laps late
  stops_analysed: number;
  race_uts: TeamRaceUts[];       // per-race breakdown for bar chart
  best_stops: PitStopDetail[];         // top 3 by UTS
  worst_stops: PitStopDetail[];        // bottom 3 by UTS
}

// ── Circuit analysis ──────────────────────────────────
export interface CircuitAnalysis {
  circuit_key: string;
  circuit_name: string;
  circuit_type: 'street' | 'permanent' | 'hybrid';
  pit_loss_estimate: number;
  avg_gap_behind: number;
  avg_uts: number;
  negative_uts_rate: number;     // 0–1
  late_call_position_correlation: number;   // −1 to +1
  circuit_punishment_score: number;
  uts_distribution: { bucket: string; count: number }[];
  stops_analysed: number;
}