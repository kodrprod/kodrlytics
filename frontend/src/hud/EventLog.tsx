import { useEffect, useRef } from 'react'
import type { PipelineEvent } from '../types'

const ACCENT = '#FF6600'
const BLACK  = '#111111'

interface EventLogProps {
  events: PipelineEvent[]
}

function eventToLine(e: PipelineEvent): { text: string; color: string } {
  switch (e.event_type) {
    case 'stage_started':    return { text: `> ${e.stage.toUpperCase()} started`, color: ACCENT }
    case 'stage_done':       return { text: `[OK] ${e.stage.toUpperCase()} done (${e.duration_ms}ms)`, color: '#009933' }
    case 'data_passed':      return { text: `-> ${e.summary}`, color: '#555555' }
    case 'finding_created':  return { text: `  ${e.name}: ${e.value?.toFixed(1)} ${e.unit}`, color: '#333333' }
    case 'flag_raised':      return {
      text: `[${e.severity.toUpperCase()}] ${e.metric}: ${e.message.slice(0, 55)}`,
      color: e.severity === 'critical' ? '#CC0000' : '#FF8800',
    }
    case 'room_opened':      return { text: `>> ${e.room_name.toUpperCase()} ROOM opened (${e.task_count} tasks)`, color: ACCENT }
    case 'worker_spawned':   return { text: `  +worker ${e.worker_id}: ${e.task_title.slice(0, 30)}`, color: '#555555' }
    case 'worker_learning':  return { text: `  ~ ${e.worker_id} learning...`, color: '#0055EE' }
    case 'worker_working':   return { text: `  > ${e.worker_id} working: ${e.task_title.slice(0, 25)}`, color: ACCENT }
    case 'worker_done':      return { text: `  [x] ${e.worker_id} done: ${e.task_title.slice(0, 25)}`, color: '#009933' }
    case 'manager_writing':  return { text: `  MGR writing report for ${e.room_name}...`, color: ACCENT }
    case 'room_closed':      return { text: `<< ${e.room_name.toUpperCase()} ROOM closed`, color: '#009933' }
    case 'run_complete':     return { text: `[COMPLETE] ${e.finding_count} findings, ${e.flag_count} flags`, color: '#009933' }
    case 'run_error':        return { text: `[ERR] ${e.error.slice(0, 70)}`, color: '#CC0000' }
    default:                 return { text: JSON.stringify(e).slice(0, 55), color: '#AAAAAA' }
  }
}

export function EventLog({ events }: EventLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  return (
    <div style={{
      overflowY: 'auto', fontSize: 11,
      fontFamily: 'Arial, sans-serif', lineHeight: 1.7,
      color: '#333',
    }}>
      {events.length === 0 && (
        <div style={{ color: '#AAAAAA', fontSize: 11 }}>
          — awaiting events —
        </div>
      )}
      {events.map((e, i) => {
        const { text, color } = eventToLine(e)
        return (
          <div key={i} style={{
            color, borderBottom: '1px solid #F5F5F5', padding: '2px 0',
            wordBreak: 'break-word',
          }}>
            {text}
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
