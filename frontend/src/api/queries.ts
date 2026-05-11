// ─────────────────────────────────────────────────────────
// api/queries.ts
// React Query (v3) query keys + fetcher functions.
// Endpoint paths match the backend routers exactly.
// ─────────────────────────────────────────────────────────

import { useQuery } from 'react-query'
import client from './client'
import type {
  Season,
  Race,
  PitStopDetail,
  RaceTimeline,
} from './types'

// ── Query keys ────────────────────────────────────────────

export const queryKeys = {
  seasons:  ['seasons'] as const,
  races:    (season: number)    => ['races', season] as const,
  pitStops: (sessionId: string) => ['pit-stops', sessionId] as const,
  timeline: (sessionId: string) => ['timeline', sessionId] as const,
}

// ── Fetchers ─────────────────────────────────────────────

async function fetchSeasons(): Promise<Season[]> {
  const { data } = await client.get<Season[]>('/seasons')
  return data
}

async function fetchRaces(season: number): Promise<Race[]> {
  const { data } = await client.get<Race[]>(`/seasons/${season}/races`)
  return data
}

async function fetchPitStops(sessionId: string): Promise<PitStopDetail[]> {
  // exclude_sc=false so we get everything; TimelineView filters for display
  const { data } = await client.get<PitStopDetail[]>(
    `/races/${sessionId}/pit-stops?exclude_sc=false`
  )
  return data
}

async function fetchTimeline(sessionId: string): Promise<RaceTimeline> {
  const { data } = await client.get<RaceTimeline>(`/races/${sessionId}/timeline`)
  return data
}

// ── Hooks ─────────────────────────────────────────────────

export function useSeasons() {
  return useQuery({
    queryKey: queryKeys.seasons,
    queryFn: fetchSeasons,
    staleTime: Infinity,
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