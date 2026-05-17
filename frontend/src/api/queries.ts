// ─────────────────────────────────────────────────────────
// api/queries.ts
// React Query hooks. All types match the actual FastAPI
// response shapes defined in types.ts.
// ─────────────────────────────────────────────────────────

import { useQuery } from 'react-query'
import client from './client'
import type {
  Season,
  Race,
  PitStopDetail,
  RaceTimeline,
  TeamList,
  TeamStrategyProfile,
  CircuitAnalysis,
  UndercutRanking,
} from './types'

// ── Query keys ────────────────────────────────────────────

export const queryKeys = {
  seasons:         ['seasons'] as const,
  races:           (season: number)      => ['races', season] as const,
  pitStops:        (sessionId: string)   => ['pit-stops', sessionId] as const,
  timeline:        (sessionId: string)   => ['timeline', sessionId] as const,
  teams:           (season?: number)     => ['teams', season ?? 'all'] as const,
  teamProfile:     (team: string, season?: number) => ['team-profile', team, season ?? 'all'] as const,
  circuitAnalysis: (key: string, season?: number)  => ['circuit-analysis', key, season ?? 'all'] as const,
  insights:        (season?: number, limit?: number) => ['insights', season ?? 'all', limit ?? 10] as const,
}

// ── Hooks — seasons + races ───────────────────────────────

export function useSeasons() {
  return useQuery(
    queryKeys.seasons,
    () => client.get<Season[]>('/seasons').then(r => r.data),
    { staleTime: Infinity }
  )
}

export function useRaces(season: number | null) {
  return useQuery(
    queryKeys.races(season ?? 0),
    () => client.get<Race[]>(`/seasons/${season}/races`).then(r => r.data),
    { enabled: season !== null, staleTime: Infinity }
  )
}

// ── Hooks — race detail ───────────────────────────────────

export function usePitStops(sessionId: string | null, excludeSc = false) {
  return useQuery(
    queryKeys.pitStops(sessionId ?? ''),
    () =>
      client
        .get<PitStopDetail[]>(`/races/${sessionId}/pit-stops`, {
          params: { exclude_sc: excludeSc },
        })
        .then(r => r.data),
    { enabled: sessionId !== null, staleTime: 5 * 60 * 1000 }
  )
}

export function useTimeline(sessionId: string | null) {
  return useQuery(
    queryKeys.timeline(sessionId ?? ''),
    () => client.get<RaceTimeline>(`/races/${sessionId}/timeline`).then(r => r.data),
    { enabled: sessionId !== null, staleTime: 5 * 60 * 1000 }
  )
}

// ── Hooks — teams ─────────────────────────────────────────

/**
 * Distinct team names for a season (or all seasons).
 * Used to populate the team selector in TeamsView.
 */
export function useTeams(season?: number) {
  return useQuery(
    queryKeys.teams(season),
    () =>
      client
        .get<TeamList>('/teams', { params: season ? { season } : {} })
        .then(r => r.data),
    { staleTime: Infinity }
  )
}

/**
 * Full strategy profile for a team.
 * season is optional — omit to get all seasons combined.
 * The response always contains a `seasons` array.
 */
export function useTeamProfile(team: string, season?: number) {
  return useQuery(
    queryKeys.teamProfile(team, season),
    () =>
      client
        .get<TeamStrategyProfile>(`/teams/${encodeURIComponent(team)}/strategy-profile`, {
          params: season ? { season } : {},
        })
        .then(r => r.data),
    { enabled: !!team }
  )
}

// ── Hooks — circuits ──────────────────────────────────────

/**
 * Circuit-level UTS patterns.
 * season is optional — omit to aggregate across all computed seasons.
 */
export function useCircuitAnalysis(circuitKey: string, season?: number) {
  return useQuery(
    queryKeys.circuitAnalysis(circuitKey, season),
    () =>
      client
        .get<CircuitAnalysis>(`/circuits/${circuitKey}/analysis`, {
          params: season ? { season } : {},
        })
        .then(r => r.data),
    { enabled: !!circuitKey }
  )
}

// ── Hooks — insights ──────────────────────────────────────

/**
 * Best and worst UTS stops across all seasons (or one season).
 * Returns { best: RankedStop[], worst: RankedStop[] }.
 */
export function useInsights(season?: number, limit = 10) {
  return useQuery(
    queryKeys.insights(season, limit),
    () =>
      client
        .get<UndercutRanking>('/insights/undercut-ranking', {
          params: { limit, ...(season ? { season } : {}) },
        })
        .then(r => r.data),
    { staleTime: 5 * 60 * 1000 }
  )
}