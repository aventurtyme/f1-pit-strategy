import { useQuery } from 'react-query'
import client from './client'
import type {
  Season,
  Race,
  PitStopDetail,
  RaceTimeline,
  TeamStrategyProfile,
  CircuitAnalysis,
} from './types'

// ── Query keys ────────────────────────────────────────────

export const queryKeys = {
  seasons:  ['seasons'] as const,
  races:    (season: number)    => ['races', season] as const,
  pitStops: (sessionId: string) => ['pit-stops', sessionId] as const,
  timeline: (sessionId: string) => ['timeline', sessionId] as const,
}

// ── Fetchers ──────────────────────────────────────────────

async function fetchSeasons(): Promise<Season[]> {
  const { data } = await client.get<Season[]>('/seasons')
  return data
}

async function fetchRaces(season: number): Promise<Race[]> {
  const { data } = await client.get<Race[]>(`/seasons/${season}/races`)
  return data
}

async function fetchPitStops(sessionId: string): Promise<PitStopDetail[]> {
  const { data } = await client.get<PitStopDetail[]>(
    `/races/${sessionId}/pit-stops?exclude_sc=false`
  )
  return data
}

async function fetchTimeline(sessionId: string): Promise<RaceTimeline> {
  const { data } = await client.get<RaceTimeline>(`/races/${sessionId}/timeline`)
  return data
}

// ── Hooks — existing (v3 positional syntax) ───────────────

export function useSeasons() {
  return useQuery(
    queryKeys.seasons,
    fetchSeasons,
    { staleTime: Infinity }
  )
}

export function useRaces(season: number | null) {
  return useQuery(
    queryKeys.races(season ?? 0),
    () => fetchRaces(season!),
    { enabled: season !== null, staleTime: Infinity }
  )
}

export function usePitStops(sessionId: string | null) {
  return useQuery(
    queryKeys.pitStops(sessionId ?? ''),
    () => fetchPitStops(sessionId!),
    { enabled: sessionId !== null, staleTime: 5 * 60 * 1000 }
  )
}

export function useTimeline(sessionId: string | null) {
  return useQuery(
    queryKeys.timeline(sessionId ?? ''),
    () => fetchTimeline(sessionId!),
    { enabled: sessionId !== null, staleTime: 5 * 60 * 1000 }
  )
}

// ── Hooks — phase 5 ───────────────────────────────────────

export function useTeamProfile(team: string, season: number) {
  return useQuery(
    ['team-profile', team, season],
    () =>
      client
        .get<TeamStrategyProfile>(`/teams/${encodeURIComponent(team)}/strategy-profile`, {
          params: { season },
        })
        .then(r => r.data),
    { enabled: !!team && !!season }
  )
}

export function useCircuitAnalysis(circuitKey: string) {
  return useQuery(
    ['circuit-analysis', circuitKey],
    () =>
      client
        .get<CircuitAnalysis>(`/circuits/${circuitKey}/analysis`)
        .then(r => r.data),
    { enabled: !!circuitKey }
  )
}

export function useInsights() {
  return useQuery(
    ['insights'],
    () =>
      client
        .get<{ findings: { id: string; text: string; polarity: 'positive' | 'negative' | 'neutral' }[] }>(
          '/insights/undercut-ranking'
        )
        .then(r => r.data)
  )
}