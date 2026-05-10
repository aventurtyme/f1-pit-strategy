// ─────────────────────────────────────────────────────────
// api/types.ts
// TypeScript types mirroring the FastAPI/Pydantic schemas
// defined in the PRD. Keep in sync with backend schemas/.
// ─────────────────────────────────────────────────────────

// ── GET /seasons ──────────────────────────────────────────

export interface Season {
  season: number;
  race_count: number;
}

// ── GET /seasons/{season}/races ───────────────────────────

export interface Race {
  session_id: string;   // uuid
  season: number;
  round: number;
  circuit_key: string;
  circuit_name: string;
  race_date: string;    // ISO date string
  computed_at: string | null;
}

// ── Shared pit-stop shape ─────────────────────────────────

export type StrategyType = 'proactive' | 'reactive' | 'neutral';
export type RaceFlag     = 'green' | 'yellow' | 'sc' | 'vsc' | 'red';

export interface PitStop {
  id: string;
  session_id: string;
  driver_code: string;
  team: string;
  lap: number;
  tire_age_self: number;
  compound_self: string;
  gap_behind: number;
  tire_age_behind: number;
  compound_behind: string;
  ptl: number;
  ppd: number;
  uts: number;
  strategy_type: StrategyType;
  pit_loss_used: number;
  race_flag: RaceFlag;
  is_opportunistic: boolean;
}

// ── GET /races/{session_id}/pit-stops ────────────────────

export type PitStopsResponse = PitStop[];

// ── GET /races/{session_id}/timeline ─────────────────────
// The timeline endpoint returns per-driver rows so the
// frontend can render each driver's race trace.

export interface DriverLap {
  lap: number;
  position: number;
  lap_time_ms: number | null;
}

export interface TimelineDriver {
  driver_code: string;
  team: string;
  finish_position: number | null;
  laps: DriverLap[];
  pit_stops: PitStop[];
}

export interface TimelineResponse {
  session_id: string;
  season: number;
  round: number;
  circuit_name: string;
  total_laps: number;
  drivers: TimelineDriver[];
}