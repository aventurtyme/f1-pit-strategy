// ─────────────────────────────────────────────────────────
// components/timeline/RaceTimeline.tsx
//
// Accepts DriverRow[] — each row has driver_code + pit_stops[].
// totalLaps is derived from the max lap seen in pit_stops since
// the /timeline endpoint doesn't return it directly.
// (If you later add total_laps to the backend schema, pass it as prop.)
// ─────────────────────────────────────────────────────────

import { useEffect, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import * as d3 from 'd3'
import type { DriverRow, MergedPitStop } from '../../api/types'
import PitStopTooltip from './PitStopTooltip'
import styles from './RaceTimeline.module.css'

interface Props {
  drivers: DriverRow[]
  circuitName: string
  /** Override total laps if known (e.g. from a future backend field). */
  totalLaps?: number
}

const MARGIN     = { top: 24, right: 24, bottom: 36, left: 48 }
const ROW_HEIGHT = 28
const MARKER_R   = 5

function markerStroke(uts: number | null): string {
  if (uts == null)  return 'var(--text-disabled)'   // SC stop — no score
  if (uts > 0)      return 'var(--uts-pos-text)'
  if (uts < 0)      return 'var(--uts-neg-text)'
  return 'var(--text-tertiary)'
}

export default function RaceTimeline({ drivers, circuitName, totalLaps }: Props) {
  const svgRef     = useRef<SVGSVGElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const [hovered, setHovered] = useState<{
    pitStop: MergedPitStop
    anchor: SVGCircleElement
  } | null>(null)

  const onMouseEnter = useCallback(
    function (this: SVGCircleElement, _: MouseEvent, d: MergedPitStop) {
      setHovered({ pitStop: d, anchor: this })
    }, []
  )
  const onMouseLeave = useCallback(() => setHovered(null), [])

  useEffect(() => {
    if (!svgRef.current || !wrapperRef.current || drivers.length === 0) return

    // Derive total laps from data if not provided
    const maxLap = totalLaps ?? Math.max(
      ...drivers.flatMap((d) => d.pit_stops.map((s) => s.lap)),
      57 // sensible fallback
    )

    const containerW = wrapperRef.current.clientWidth
    const innerW     = containerW - MARGIN.left - MARGIN.right
    const innerH     = drivers.length * ROW_HEIGHT
    const totalH     = innerH + MARGIN.top + MARGIN.bottom

    const svg = d3.select(svgRef.current)
      .attr('width', containerW)
      .attr('height', totalH)

    svg.selectAll('*').remove()

    const g = svg.append('g')
      .attr('transform', `translate(${MARGIN.left},${MARGIN.top})`)

    const xScale = d3.scaleLinear()
      .domain([1, maxLap])
      .range([0, innerW])

    // X axis
    g.append('g')
      .attr('transform', `translate(0,${innerH + 8})`)
      .call(
        d3.axisBottom(xScale)
          .ticks(Math.min(maxLap, 12))
          .tickFormat((d) => `L${d}`)
          .tickSize(0)
      )
      .call((ax) => {
        ax.select('.domain').remove()
        ax.selectAll('text')
          .attr('font-family', 'var(--font-mono)')
          .attr('font-size', '10px')
          .attr('fill', 'var(--text-tertiary)')
          .attr('letter-spacing', '0.08em')
      })

    // Driver rows
    drivers.forEach((driver, i) => {
      const y = i * ROW_HEIGHT + ROW_HEIGHT / 2

      // Driver code label
      g.append('text')
        .attr('x', -8).attr('y', y).attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .attr('font-family', 'var(--font-mono)')
        .attr('font-size', '11px').attr('font-weight', '500')
        .attr('fill', 'var(--text-secondary)')
        .text(driver.driver_code)

      // Track line
      g.append('line')
        .attr('x1', 0).attr('x2', innerW)
        .attr('y1', y).attr('y2', y)
        .attr('stroke', 'var(--bg-border-strong)')
        .attr('stroke-width', 1.5)
        .attr('stroke-linecap', 'round')

      // Pit stop markers
      g.append('g')
        .selectAll<SVGCircleElement, MergedPitStop>('circle')
        .data(driver.pit_stops)
        .join('circle')
        .attr('cx', (d) => xScale(d.lap))
        .attr('cy', y)
        .attr('r', MARKER_R)
        .attr('fill', 'var(--bg-base)')
        .attr('stroke', (d) => markerStroke(d.uts))
        .attr('stroke-width', 1.5)
        .style('cursor', 'pointer')
        .style('transition', 'transform 150ms ease-out')
        .on('mouseenter', onMouseEnter)
        .on('mouseleave', onMouseLeave)
    })

    // Row dividers
    drivers.forEach((_, i) => {
      if (i === 0) return
      g.append('line')
        .attr('x1', 0).attr('x2', innerW)
        .attr('y1', i * ROW_HEIGHT).attr('y2', i * ROW_HEIGHT)
        .attr('stroke', 'var(--bg-border)')
        .attr('stroke-width', 1)
        .lower()
    })
  }, [drivers, totalLaps, onMouseEnter, onMouseLeave])

  if (drivers.length === 0) {
    return (
      <div className={styles.wrapper}>
        <p className={styles.empty}>No pit stop data available for this session.</p>
      </div>
    )
  }

  return (
    <div ref={wrapperRef} className={styles.wrapper}>
      <div className={styles.header}>
        <span style={{ fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
          {circuitName}
        </span>
        <span className="label-micro">{drivers.length} drivers</span>
      </div>

      <svg ref={svgRef} className={styles.svg} aria-label="Race timeline" />

      <div className={styles.legend}>
        {[
          { cls: styles.dotPos, label: 'UTS positive' },
          { cls: styles.dotNeg, label: 'UTS negative' },
          { cls: styles.dotNeu, label: 'UTS neutral'  },
          { cls: styles.dotSc,  label: 'SC / no score'},
        ].map(({ cls, label }) => (
          <div key={label} className={styles.legendItem}>
            <span className={`${styles.dot} ${cls}`} />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {hovered && createPortal(
        <PitStopTooltip
          pitStop={hovered.pitStop}
          anchorEl={hovered.anchor}
          circuitName={circuitName}
        />,
        document.body
      )}
    </div>
  )
}