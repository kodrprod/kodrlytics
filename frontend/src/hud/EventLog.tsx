import { useEffect, useRef } from 'react'
import type { PipelineEvent } from '../types'

interface EventLogProps {
  events: PipelineEvent[]
}

function eventToLine(e: PipelineEvent): { text: string; color: string } {
  switch (e.event_type) {
    case 'stage_started': return { text: `▶ ${e.stage.toUpperCase()} started`, color: '#00ccff' }
    case 'stage_done':    return { text: `✓ ${e.stage.toUpperCase()} done (${e.duration_ms}ms)`, color: '#00ff88' }
    case 'data_passed':   return { text: `→ ${e.summary}`, color: '#88aacc' }
    case 'finding_created': return { text: `  ${e.name}: ${e.value?.toFixed(1)} ${e.unit}`, color: '#aaccee' }
    case 'flag_raised':   return { text: `⚠ [${e.severity.toUpperCase()}] ${e.metric}: ${e.message.slice(0, 60)}...`, color: e.severity === 'critical' ? '#ff4444' : '#ffaa00' }
    case 'run_complete':  return { text: `✅ COMPLETE — ${e.finding_count} findings, ${e.flag_count} flags`, color: '#00ff88' }
    case 'run_error':     return { text: `❌ ERROR: ${e.error.slice(0, 80)}`, color: '#ff4444' }
    default:              return { text: JSON.stringify(e).slice(0, 60), color: '#666' }
  }
}

export function EventLog({ events }: EventLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  return (
    <div style={{ flex: 1, overflowY: 'auto', fontSize: '11px', fontFamily: 'monospace', lineHeight: '1.7' }}>
      {events.map((e, i) => {
        const { text, color } = eventToLine(e)
        return (
          <div key={i} style={{ color, padding: '1px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
            {text}
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
