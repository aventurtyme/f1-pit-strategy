// ─────────────────────────────────────────────────────────
// components/timeline/RaceTimeline.tsx
//
// D3 rendering strategy:
//   - React owns the <svg> container ref; D3 owns everything
//     inside it (enter/update/exit pattern via selection.join).
//   - Tooltip is a React portal rendered outside the SVG to
//     avoid SVG foreignObject quirks.
//   - Hover state is kept in React state so the portal
//     re-renders correctly.
//   - All colours reference CSS variables via getComputedStyle
//     so the design-token layer is never bypassed.
// ─────────────────────────────────────────────────────────

import { useEffect, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import * as d3 from 'd3'
import type { TimelineDriver, PitStop } from '../../api/types'
import PitStopTooltip from './PitStopTooltip'
import styles from './RaceTimeline.module.css'

interface Props {
  drivers: TimelineDriver[]
  totalLaps: number
  circuitName: string
}

// ── Layout constants ───────────────────────────────────────
const MARGIN       = { top: 24, right: 24, bottom: 36, left: 48 }
const ROW_HEIGHT   = 28  // px per driver row
const MARKER_R     = 5   // marker radius (10px diameter per style guide)

// ── Colour helpers ────────────────────────────────────────
function markerClass(uts: number): string {
  if (uts > 0) return 'pos'
  if (uts < 0) return 'neg'
  return 'neu'
}

function markerStroke(uts: number): string {
  if (uts > 0) return 'var(--uts-pos-text)'
  if (uts < 0) return 'var(--uts-neg-text)'
  return 'var(--text-tertiary)'
}

export default function RaceTimeline({ drivers, totalLaps, circuitName }: Props) {
  const svgRef     = useRef<SVGSVGElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const [hovered, setHovered] = useState<{
    pitStop: PitStop
    anchor: SVGCircleElement
  } | null>(null)

  // ── Stable callbacks for D3 event handlers ─────────────
  const onMouseEnter = useCallback(
    function (this: SVGCircleElement, _: MouseEvent, d: PitStop) {
      setHovered({ pitStop: d, anchor: this })
    },
    []
  )

  const onMouseLeave = useCallback(() => {
    setHovered(null)
  }, [])

  // ── Draw / update chart ────────────────────────────────
  useEffect(() => {
    if (!svgRef.current || !wrapperRef.current) return

    const containerW = wrapperRef.current.clientWidth
    const innerW     = containerW - MARGIN.left - MARGIN.right
    const innerH     = drivers.length * ROW_HEIGHT

    const totalH = innerH + MARGIN.top + MARGIN.bottom

    // ── SVG root ──────────────────────────────────────────
    const svg = d3.select(svgRef.current)
      .attr('width', containerW)
      .attr('height', totalH)

    // Clear on each render (driver list may change)
    svg.selectAll('*').remove()

    const g = svg.append('g')
      .attr('transform', `translate(${MARGIN.left},${MARGIN.top})`)

    // ── Scales ────────────────────────────────────────────
    const xScale = d3.scaleLinear()
      .domain([1, totalLaps])
      .range([0, innerW])

    // ── X-axis ────────────────────────────────────────────
    const xAxis = d3.axisBottom(xScale)
      .ticks(Math.min(totalLaps, 12))
      .tickFormat((d) => `L${d}`)
      .tickSize(0)

    g.append('g')
      .attr('transform', `translate(0,${innerH + 8})`)
      .call(xAxis)
      .call((ax) => {
        ax.select('.domain').remove()
        ax.selectAll('text')
          .attr('font-family', 'var(--font-mono)')
          .attr('font-size', '10px')
          .attr('fill', 'var(--text-tertiary)')
          .attr('letter-spacing', '0.08em')
      })

    // ── Driver rows ───────────────────────────────────────
    drivers.forEach((driver, i) => {
      const y = i * ROW_HEIGHT + ROW_HEIGHT / 2

      // Driver code label
      g.append('text')
        .attr('x', -8)
        .attr('y', y)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .attr('font-family', 'var(--font-mono)')
        .attr('font-size', '11px')
        .attr('font-weight', '500')
        .attr('fill', 'var(--text-secondary)')
        .text(driver.driver_code)

      // Track line
      g.append('line')
        .attr('x1', 0)
        .attr('x2', innerW)
        .attr('y1', y)
        .attr('y2', y)
        .attr('stroke', 'var(--bg-border-strong)')
        .attr('stroke-width', 1.5)
        .attr('stroke-linecap', 'round')

      // Pit stop markers
      const markerGroup = g.append('g').attr('class', 'markers')

      markerGroup.selectAll<SVGCircleElement, PitStop>('circle')
        .data(driver.pit_stops)
        .join('circle')
        .attr('cx', (d) => xScale(d.lap))
        .attr('cy', y)
        .attr('r', MARKER_R)
        .attr('fill', 'var(--bg-base)')
        .attr('stroke', (d) => markerStroke(d.uts))
        .attr('stroke-width', 1.5)
        .attr('class', (d) => `pit-marker ${markerClass(d.uts)}`)
        .style('cursor', 'pointer')
        .style('transition', 'transform 150ms ease-out')
        .on('mouseenter', onMouseEnter)
        .on('mouseleave', onMouseLeave)
    })

    // ── Horizontal grid lines at each row boundary ─────────
    drivers.forEach((_, i) => {
      if (i === 0) return
      g.append('line')
        .attr('x1', 0)
        .attr('x2', innerW)
        .attr('y1', i * ROW_HEIGHT)
        .attr('y2', i * ROW_HEIGHT)
        .attr('stroke', 'var(--bg-border)')
        .attr('stroke-width', 1)
        .lower() // push behind markers
    })
  }, [drivers, totalLaps, onMouseEnter, onMouseLeave])

  return (
    <div ref={wrapperRef} className={styles.wrapper}>
      <svg ref={svgRef} className={styles.svg} aria-label="Race timeline" />

      {/* Legend */}
      <div className={styles.legend}>
        {[
          { cls: styles.dotPos, label: 'UTS positive' },
          { cls: styles.dotNeg, label: 'UTS negative' },
          { cls: styles.dotNeu, label: 'UTS neutral'  },
        ].map(({ cls, label }) => (
          <div key={label} className={styles.legendItem}>
            <span className={`${styles.dot} ${cls}`} />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {/* Tooltip portal */}
      {hovered &&
        createPortal(
          <PitStopTooltip
            pitStop={hovered.pitStop}
            anchorEl={hovered.anchor}
            circuitName={circuitName}
          />,
          document.body
        )
      }
    </div>
  )
}