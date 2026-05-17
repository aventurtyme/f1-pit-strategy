// ─────────────────────────────────────────────────────────
// views/TeamsView.tsx
// Season + team selector with full strategy dashboard.
// Mirrors the "Teams" panel in layout_proposal.html.
// Season selector uses segmented control; team selector uses pills.
// Data comes from useTeams() (list) + useTeamProfile() (detail).
// ─────────────────────────────────────────────────────────

import { useState } from 'react'
import { useTeams, useTeamProfile, useSeasons } from '../api/queries'
import { StopRatioBar } from '../components/charts/StopRatioBar'
import { StopCard } from '../components/cards/StopCard'
import SkeletonRow from '../components/SkeletonRow'
import styles from './TeamsView.module.css'

function signed(v: number | null, decimals = 1): string {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(decimals)}`
}

export function TeamsView() {
  const { data: seasons } = useSeasons()
  const availableSeasons = seasons?.map(s => s.season).sort((a, b) => b - a) ?? []

  const [selectedSeason, setSelectedSeason] = useState<number | undefined>(undefined)
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null)

  const { data: teamList, isLoading: teamsLoading } = useTeams(selectedSeason)

  // Auto-select first team when list loads or season changes
  const teams = teamList?.teams ?? []
  const activeTeam = selectedTeam && teams.includes(selectedTeam)
    ? selectedTeam
    : teams[0] ?? null

  const { data: profile, isLoading: profileLoading, isError } =
    useTeamProfile(activeTeam ?? '', selectedSeason)

  // Derive stats from the matching season entry (or first if no filter)
  const seasonStats = profile
    ? selectedSeason
      ? profile.seasons.find(s => s.season === selectedSeason) ?? profile.seasons[0]
      : profile.seasons[profile.seasons.length - 1]   // most recent season
    : null

  const isLoading = teamsLoading || profileLoading

  return (
    <div className={styles.page}>

      {/* ── Control bar ── */}
      <div className={styles.ctrl}>
        <span className={styles.ctrlLabel}>Season</span>
        <div className={styles.seasonSeg}>
          <button
            className={`${styles.segBtn} ${!selectedSeason ? styles.segActive : ''}`}
            onClick={() => setSelectedSeason(undefined)}
          >
            All
          </button>
          {availableSeasons.map(s => (
            <button
              key={s}
              className={`${styles.segBtn} ${selectedSeason === s ? styles.segActive : ''}`}
              onClick={() => setSelectedSeason(s)}
            >
              {s}
            </button>
          ))}
        </div>

        {teams.length > 0 && (
          <>
            <div className={styles.divider} />
            <span className={styles.ctrlLabel}>Team</span>
            <div className={styles.teamPills}>
              {teams.map(t => (
                <button
                  key={t}
                  className={`${styles.pill} ${activeTeam === t ? styles.pillActive : ''}`}
                  onClick={() => setSelectedTeam(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* ── Body ── */}
      <div className={styles.body}>

        {isLoading && (
          <div className={styles.skeletons}>
            {[1, 2, 3, 4].map(i => <SkeletonRow key={i} />)}
          </div>
        )}

        {!isLoading && (isError || !profile || !seasonStats) && (
          <p className={styles.empty}>
            No data available for this team.
          </p>
        )}

        {!isLoading && profile && seasonStats && (
          <>
            {/* ── Team heading ── */}
            <div className={styles.teamHeading}>
              <h1 className={styles.teamName}>{profile.team}</h1>
              <span className={styles.seasonLabel}>
                {selectedSeason ? `${selectedSeason} season` : 'all seasons'}
              </span>
            </div>

            {/* ── Stat strip ── */}
            <div className={styles.statRow}>
              {[
                {
                  label: 'Avg UTS',
                  value: signed(seasonStats.avg_uts),
                  sub: 'across scored stops',
                  colored: true,
                  colorVal: seasonStats.avg_uts,
                },
                {
                  label: 'Reactive rate',
                  value: `${seasonStats.reactive_stop_rate.toFixed(1)}%`,
                  sub: 'of stops under threat',
                  colored: false,
                  colorVal: null,
                },
                {
                  label: 'Total stops',
                  value: `${seasonStats.total_green_stops}`,
                  sub: 'green-flag scored',
                  colored: false,
                  colorVal: null,
                },
                {
                  label: 'Opportunistic',
                  value: `${seasonStats.opportunistic_stops}`,
                  sub: 'of total stops',
                  colored: false,
                  colorVal: null,
                },
              ].map(s => (
                <div key={s.label} className={styles.statCard}>
                  <p className={styles.statLabel}>{s.label}</p>
                  <p
                    className={styles.statValue}
                    style={
                      s.colored && s.colorVal != null
                        ? {
                            color:
                              s.colorVal >= 0
                                ? 'var(--uts-pos-text)'
                                : 'var(--uts-neg-text)',
                          }
                        : {}
                    }
                  >
                    {s.value}
                  </p>
                  <p className={styles.statSub}>{s.sub}</p>
                </div>
              ))}
            </div>

            {/* ── Stop distribution chart ── */}
            <div className={styles.chartCard}>
              <p className={styles.chartLabel}>Stop distribution</p>
              <div style={{ marginTop: '1rem' }}>
                <StopRatioBar
                  proactive={seasonStats.proactive_stops}
                  reactive={seasonStats.reactive_stops}
                  neutral={seasonStats.neutral_stops}
                />
              </div>
            </div>

            {/* ── Best / worst stops ── */}
            {(profile.best_stop || profile.worst_stop) && (
              <div className={styles.stopsRow}>
                {profile.best_stop && (
                  <div>
                    <p className={styles.chartLabel}>Best stop</p>
                    <div className={styles.stopsList}>
                      <StopCard stop={profile.best_stop} rank="best" />
                    </div>
                  </div>
                )}
                {profile.worst_stop && (
                  <div>
                    <p className={styles.chartLabel}>Worst stop</p>
                    <div className={styles.stopsList}>
                      <StopCard stop={profile.worst_stop} rank="worst" />
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}