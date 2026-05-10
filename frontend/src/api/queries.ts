// ─────────────────────────────────────────────────────────
// api/queries.ts
// React Query (v3) query keys + fetcher functions.
// One fetcher per endpoint — no business logic here.
// ─────────────────────────────────────────────────────────

import { useQuery } from 'react-query'
import client from './client'
import type {
  Season,
  Race,
  PitStopsResponse,
  TimelineResponse,
} from './types'

// ── Query keys (tuple arrays for granular invalidation) ──

export const queryKeys = {
  seasons:     ['seasons'] as const,
  races:       (season: number) => ['races', season] as const,
  pitStops:    (sessionId: string) => ['pit-stops', sessionId] as const,
  timeline:    (sessionId: string) => ['timeline', sessionId] as const,
} as const

// ── Fetchers ─────────────────────────────────────────────

async function fetchSeasons(): Promise<Season[]> {
  const { data } = await client.get<Season[]>('/seasons')
  return data
}

async function fetchRaces(season: number): Promise<Race[]> {
  const { data } = await client.get<Race[]>(`/seasons/${season}/races`)
  return data
}

async function fetchPitStops(sessionId: string): Promise<PitStopsResponse> {
  const { data } = await client.get<PitStopsResponse>(`/races/${sessionId}/pit-stops`)
  return data
}

async function fetchTimeline(sessionId: string): Promise<TimelineResponse> {
  const { data } = await client.get<TimelineResponse>(`/races/${sessionId}/timeline`)
  return data
}

// ── Hooks ────────────────────────────────────────────────

export function useSeasons() {
  return useQuery({
    queryKey: queryKeys.seasons,
    queryFn: fetchSeasons,
    staleTime: Infinity, // seasons list rarely changes mid-session
  })
}

export function useRaces(season: number | null) {
  return useQuery({
    queryKey: queryKeys.races(season ?? 0),
    queryFn: () => fetchRaces(season!),
    enabled: season !== null,
    staleTime: Infinity,
  })
}

export function usePitStops(sessionId: string | null) {
  return useQuery({
    queryKey: queryKeys.pitStops(sessionId ?? ''),
    queryFn: () => fetchPitStops(sessionId!),
    enabled: sessionId !== null,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTimeline(sessionId: string | null) {
  return useQuery({
    queryKey: queryKeys.timeline(sessionId ?? ''),
    queryFn: () => fetchTimeline(sessionId!),
    enabled: sessionId !== null,
    staleTime: 5 * 60 * 1000,
  })
}