import { useState, useEffect } from 'react'
import type { PipelineState } from '../hooks/usePipelineWS'
import type { WorkerInfo, WorkerStatus, RoomInfo } from '../types'

const ACCENT = '#FF6600'
const BLACK  = '#111111'
const GREY   = '#888888'

const WORKER_COLORS: Record<WorkerStatus, { bg: string; fg: string; glow: string }> = {
  idle:     { bg: '#DDDDDD', fg: '#666666', glow: 'none' },
  learning: { bg: '#0055EE', fg: '#FFFFFF', glow: '0 0 10px #0055EEAA' },
  working:  { bg: ACCENT,    fg: '#FFFFFF', glow: `0 0 10px ${ACCENT}AA` },
  stuck:    { bg: '#CC0000', fg: '#FFFFFF', glow: '0 0 10px #CC0000AA' },
  done:     { bg: '#222222', fg: '#FFFFFF', glow: 'none' },
}

interface Pos { x: number; y: number }

function deskPos(i: number): Pos {
  const col = i % 4
  const row = Math.floor(i / 4)
  return { x: 15 + col * 20, y: 52 + row * 18 }
}

function targetZone(status: WorkerStatus, i: number): Pos {
  if (status === 'learning') return { x: 8  + Math.random() * 16, y: 14 + Math.random() * 18 }
  if (status === 'stuck')    return { x: 72 + Math.random() * 14, y: 10 + Math.random() * 16 }
  const base = deskPos(i)
  if (status === 'working')  return { x: base.x + (Math.random() - 0.5) * 5, y: base.y + (Math.random() - 0.5) * 5 }
  return base
}

function useWorkerPositions(workers: WorkerInfo[]): Map<string, Pos> {
  const [pos, setPos] = useState<Map<string, Pos>>(new Map())

  const workerKey = workers.map(w => w.worker_id).join(',')
  useEffect(() => {
    setPos(prev => {
      const next = new Map(prev)
      workers.forEach((w, i) => {
        if (!next.has(w.worker_id)) next.set(w.worker_id, deskPos(i))
      })
      return next
    })
  }, [workerKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!workers.length) return
    const id = setInterval(() => {
      setPos(prev => {
        const next = new Map(prev)
        workers.forEach((w, i) => {
          const cur = next.get(w.worker_id)
          if (!cur) return
          const t = targetZone(w.status, i)
          next.set(w.worker_id, {
            x: cur.x + (t.x - cur.x) * 0.35,
            y: cur.y + (t.y - cur.y) * 0.35,
          })
        })
        return next
      })
    }, 700)
    return () => clearInterval(id)
  }, [workers]) // eslint-disable-line react-hooks/exhaustive-deps

  return pos
}

function RoomFloor({ room }: { room: RoomInfo }) {
  const positions = useWorkerPositions(room.workers)
  const progress  = room.task_count > 0 ? room.tasks_done / room.task_count : 0
  const active    = room.status === 'active'
  const statusColor = { idle: '#AAAAAA', active: ACCENT, complete: '#009933', error: '#CC0000' }[room.status]

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '16px 24px', gap: 10 }}>

      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, borderBottom: `2px solid ${statusColor}`, paddingBottom: 8 }}>
        <span style={{ fontSize: 20, fontWeight: 700, color: BLACK, letterSpacing: '0.12em' }}>
          {room.name.toUpperCase()} ROOM
        </span>
        <span style={{ fontSize: 10, color: statusColor, fontWeight: 700, letterSpacing: '0.15em' }}>
          [{room.status.toUpperCase()}]
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: GREY }}>
          {room.workers.length} workers &bull; {room.tasks_done}/{room.task_count} tasks
        </span>
      </div>

      {/* Floor canvas */}
      <div style={{
        flex: 1, position: 'relative',
        border: `2px solid ${active ? ACCENT : '#D0D0D0'}`,
        background: '#FAFAFA',
        overflow: 'hidden', minHeight: 240,
      }}>
        {/* Grid lines */}
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          backgroundImage: 'linear-gradient(rgba(0,0,0,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(0,0,0,0.04) 1px,transparent 1px)',
          backgroundSize: '36px 36px',
        }} />

        {/* ASCII corner markers */}
        <span style={{ position: 'absolute', top: 4,  left: 6,  fontSize: 9, color: '#CCCCCC', lineHeight: 1 }}>+</span>
        <span style={{ position: 'absolute', top: 4,  right: 6, fontSize: 9, color: '#CCCCCC', lineHeight: 1 }}>+</span>
        <span style={{ position: 'absolute', bottom: 4, left: 6,  fontSize: 9, color: '#CCCCCC', lineHeight: 1 }}>+</span>
        <span style={{ position: 'absolute', bottom: 4, right: 6, fontSize: 9, color: '#CCCCCC', lineHeight: 1 }}>+</span>

        {/* Manager (top-right) */}
        <div style={{ position: 'absolute', top: '5%', right: '4%', textAlign: 'center' }}>
          <div style={{
            width: 42, height: 42, borderRadius: '50%', margin: '0 auto',
            background: active ? ACCENT : '#DDDDDD',
            border: `2px solid ${BLACK}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 9, fontWeight: 700,
            color: active ? '#FFF' : GREY,
            boxShadow: active ? `0 0 16px ${ACCENT}88` : 'none',
            transition: 'all 0.5s',
            animation: active ? 'mgrPulse 2s ease-in-out infinite' : 'none',
          }}>MGR</div>
          <div style={{ fontSize: 7, color: GREY, letterSpacing: '0.1em', marginTop: 3 }}>MANAGER</div>
        </div>

        {/* Task board (top-left) */}
        {room.workers.length > 0 && (
          <div style={{
            position: 'absolute', top: '4%', left: '3%',
            border: `1px solid ${active ? ACCENT : '#CCCCCC'}`,
            background: '#FFFFFF', padding: '5px 9px', minWidth: 140,
          }}>
            <div style={{ fontSize: 8, fontWeight: 700, color: ACCENT, marginBottom: 3, letterSpacing: '0.1em' }}>
              [TASK BOARD]
            </div>
            {room.workers.slice(0, 7).map(w => (
              <div key={w.worker_id} style={{
                fontSize: 7.5, color: w.status === 'done' ? '#BBBBBB' : BLACK,
                textDecoration: w.status === 'done' ? 'line-through' : 'none',
                lineHeight: 1.6,
              }}>
                {w.status === 'done' ? '[x]' : w.status === 'working' ? '[>]' : w.status === 'learning' ? '[~]' : '[ ]'}{' '}
                {w.task_title.slice(0, 22)}
              </div>
            ))}
          </div>
        )}

        {/* Worker agents */}
        {room.workers.map((w, i) => {
          const p = positions.get(w.worker_id) ?? deskPos(i)
          const c = WORKER_COLORS[w.status]
          const label = w.worker_id.replace(/\D/g, '').slice(-2).padStart(2, '0') || String(i + 1).padStart(2, '0')
          return (
            <div key={w.worker_id}
              title={`${w.worker_id}: ${w.task_title} [${w.status}]`}
              style={{
                position: 'absolute',
                left: `calc(${p.x}% - 14px)`,
                top: `calc(${p.y}% - 14px)`,
                width: 28, height: 28, borderRadius: '50%',
                background: c.bg, border: `2px solid ${BLACK}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 7.5, fontWeight: 700, color: c.fg,
                boxShadow: c.glow,
                transition: 'left 0.7s ease, top 0.7s ease, background 0.4s, box-shadow 0.4s',
                zIndex: 2, userSelect: 'none', cursor: 'default',
                animation:
                  w.status === 'learning' ? 'wLearn 1.6s ease-in-out infinite' :
                  w.status === 'working'  ? 'wWork  1.0s ease-in-out infinite' :
                  w.status === 'stuck'    ? 'wStuck 0.4s ease-in-out infinite' : 'none',
              }}>
              {label}
            </div>
          )
        })}

        {/* Idle placeholder */}
        {room.status === 'idle' && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#CCCCCC', fontSize: 13, letterSpacing: '0.4em', pointerEvents: 'none',
          }}>
            . . . W A I T I N G . . .
          </div>
        )}

        {/* Complete overlay */}
        {room.status === 'complete' && (
          <div style={{
            position: 'absolute', bottom: 8, right: 12,
            fontSize: 10, color: '#009933', fontWeight: 700, letterSpacing: '0.15em',
          }}>
            [COMPLETE] &#10003;
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 9, color: GREY, letterSpacing: '0.1em', minWidth: 60 }}>PROGRESS</span>
        <div style={{ flex: 1, height: 5, background: '#E0E0E0', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${Math.round(progress * 100)}%`,
            background: room.status === 'complete' ? '#009933' : ACCENT,
            transition: 'width 0.5s',
          }} />
        </div>
        <span style={{ fontSize: 9, color: BLACK, minWidth: 36, textAlign: 'right' }}>
          {room.tasks_done}/{room.task_count}
        </span>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, fontSize: 9, color: GREY }}>
        {(['learning', 'working', 'done', 'idle'] as WorkerStatus[]).map(s => {
          const n = room.workers.filter(w => w.status === s).length
          if (!n) return null
          return (
            <span key={s} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{
                width: 8, height: 8, borderRadius: '50%',
                background: WORKER_COLORS[s].bg, border: '1px solid #999',
                display: 'inline-block', flexShrink: 0,
              }} />
              {s}: {n}
            </span>
          )
        })}
      </div>
    </div>
  )
}

interface FloorViewProps {
  state: PipelineState
  activeFloor: number
  onFloorChange: (i: number) => void
}

export function FloorView({ state, activeFloor, onFloorChange }: FloorViewProps) {
  const roomStatuses = state.rooms.map(r => r.status).join(',')
  useEffect(() => {
    const idx = state.rooms.findIndex(r => r.status === 'active')
    if (idx >= 0) onFloorChange(idx)
  }, [roomStatuses]) // eslint-disable-line react-hooks/exhaustive-deps

  const room = state.rooms[activeFloor]

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

      {/* Floor tabs */}
      <div style={{
        display: 'flex', background: BLACK,
        borderBottom: `3px solid ${ACCENT}`,
        flexShrink: 0, overflowX: 'auto',
      }}>
        {state.rooms.map((r, i) => {
          const on  = activeFloor === i
          const dot = { idle: '#444444', active: ACCENT, complete: '#009933', error: '#CC0000' }[r.status]
          return (
            <button key={r.name} onClick={() => onFloorChange(i)}
              style={{
                padding: '8px 15px',
                border: 'none', borderRight: '1px solid #333333',
                background: on ? '#FFFFFF' : 'transparent',
                color: on ? BLACK : '#888888',
                fontFamily: '"Courier New", monospace',
                fontSize: 11, fontWeight: on ? 700 : 400,
                cursor: 'pointer', letterSpacing: '0.08em',
                display: 'flex', alignItems: 'center', gap: 6,
                whiteSpace: 'nowrap',
                borderBottom: on ? `3px solid ${ACCENT}` : '3px solid transparent',
                transition: 'background 0.15s, color 0.15s',
                marginBottom: -3,
              }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%',
                background: dot, display: 'inline-block', flexShrink: 0,
              }} />
              F{i + 1}:{r.name.toUpperCase()}
            </button>
          )
        })}
      </div>

      {room && <RoomFloor room={room} />}

      <style>{`
        @keyframes mgrPulse { 0%,100%{box-shadow:0 0 8px ${ACCENT}88}  50%{box-shadow:0 0 22px ${ACCENT}} }
        @keyframes wLearn   { 0%,100%{transform:scale(1)}               50%{transform:scale(1.18)} }
        @keyframes wWork    { 0%,100%{transform:scale(1)}               50%{transform:scale(1.10)} }
        @keyframes wStuck   { 0%,100%{transform:translateX(0)}          50%{transform:translateX(3px)} }
      `}</style>
    </div>
  )
}
