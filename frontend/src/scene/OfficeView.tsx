import { useState, useEffect, useRef } from 'react'
import type { PipelineState } from '../hooks/usePipelineWS'
import type { WorkerInfo, WorkerStatus, RoomInfo } from '../types'

const ORANGE = '#FF6600'
const DARK   = '#1A1A1A'
const MID    = '#2D2D2D'
const LIGHT  = '#F5F5F5'
const GREY   = '#888888'

const STATUS_COLOR: Record<WorkerStatus, string> = {
  idle:     '#555555',
  learning: '#2266EE',
  working:  ORANGE,
  stuck:    '#CC2222',
  done:     '#228833',
}

const STATUS_LABEL: Record<WorkerStatus, string> = {
  idle:     'IDLE',
  learning: 'SEARCH',
  working:  'WORKING',
  stuck:    'STUCK',
  done:     'DONE',
}

// ── Worker figure ─────────────────────────────────────────────────────────────

function WorkerFigure({ worker, index }: { worker: WorkerInfo; index: number }) {
  const color = STATUS_COLOR[worker.status]
  const label = worker.worker_id.replace(/\D/g, '').slice(-2).padStart(2, '0') || String(index + 1).padStart(2, '0')
  const isActive = worker.status === 'learning' || worker.status === 'working'
  const animClass =
    worker.status === 'learning' ? 'w-learn' :
    worker.status === 'working'  ? 'w-work'  :
    worker.status === 'stuck'    ? 'w-stuck'  : ''

  return (
    <div
      title={`${worker.worker_id}: ${worker.task_title} [${worker.status}]`}
      className={animClass}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 2, cursor: 'default', userSelect: 'none',
        filter: worker.status === 'done' ? 'grayscale(0.6)' : 'none',
        opacity: worker.status === 'idle' ? 0.5 : 1,
        transition: 'opacity 0.3s, filter 0.3s',
      }}
    >
      {/* Monitor */}
      <div style={{
        width: 28, height: 20,
        background: isActive ? '#0D1B2A' : '#2A2A2A',
        border: `1px solid ${isActive ? color : '#444'}`,
        borderRadius: 2,
        position: 'relative',
        boxShadow: isActive ? `0 0 8px ${color}55` : 'none',
        transition: 'box-shadow 0.3s, border-color 0.3s',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {/* Screen content */}
        <div style={{
          width: 22, height: 14,
          background: isActive
            ? `linear-gradient(135deg, #0a2040 0%, ${color}22 100%)`
            : '#1A1A1A',
          borderRadius: 1,
          overflow: 'hidden',
        }}>
          {worker.status === 'working' && (
            <div style={{
              display: 'flex', flexDirection: 'column', gap: 1.5, padding: 2,
            }}>
              {[8, 14, 10, 12].map((w, i) => (
                <div key={i} style={{
                  height: 1.5, width: `${w}px`,
                  background: ORANGE, borderRadius: 1, opacity: 0.7,
                }} />
              ))}
            </div>
          )}
          {worker.status === 'learning' && (
            <div style={{
              width: '100%', height: '100%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                border: `1.5px solid #2266EE`,
                borderTopColor: 'transparent',
                animation: 'spin 0.8s linear infinite',
              }} />
            </div>
          )}
          {worker.status === 'done' && (
            <div style={{
              width: '100%', height: '100%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#228833', fontSize: 8, fontWeight: 700,
            }}>✓</div>
          )}
        </div>
        {/* Monitor stand */}
        <div style={{
          position: 'absolute', bottom: -4, left: '50%',
          transform: 'translateX(-50%)',
          width: 8, height: 4,
          background: '#333',
        }} />
      </div>

      {/* Desk */}
      <div style={{
        width: 36, height: 5,
        background: `linear-gradient(180deg, #5C3D1E 0%, #3D2810 100%)`,
        borderRadius: 1,
        boxShadow: '0 2px 4px rgba(0,0,0,0.4)',
      }} />

      {/* Person */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1, marginTop: 1 }}>
        {/* Head */}
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: `linear-gradient(135deg, ${color} 0%, ${color}99 100%)`,
          border: `1px solid ${color}`,
          boxShadow: isActive ? `0 0 6px ${color}88` : 'none',
          transition: 'box-shadow 0.3s',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 5, color: '#fff', fontWeight: 700,
        }}>{label}</div>
        {/* Body */}
        <div style={{
          width: 12, height: 8,
          background: `linear-gradient(180deg, ${color}CC 0%, ${color}66 100%)`,
          borderRadius: '4px 4px 0 0',
        }} />
      </div>

      {/* Status badge */}
      <div style={{
        fontSize: 6, color: color, fontWeight: 700,
        letterSpacing: '0.05em',
        background: `${color}15`,
        padding: '1px 3px', borderRadius: 2,
        border: `0.5px solid ${color}44`,
      }}>
        {STATUS_LABEL[worker.status]}
      </div>
    </div>
  )
}

// ── CEO floor ─────────────────────────────────────────────────────────────────

function CEOFloor({ active, message }: { active: boolean; message: string }) {
  return (
    <div style={{
      background: `linear-gradient(135deg, #1A0A00 0%, #2D1500 100%)`,
      border: `2px solid ${active ? ORANGE : '#333'}`,
      borderRadius: 6, padding: '10px 16px',
      display: 'flex', alignItems: 'center', gap: 16,
      boxShadow: active ? `0 0 20px ${ORANGE}33` : 'none',
      transition: 'all 0.5s',
      flexShrink: 0,
    }}>
      {/* CEO figure */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, flexShrink: 0 }}>
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: active
            ? `radial-gradient(circle, ${ORANGE} 0%, #994400 100%)`
            : `radial-gradient(circle, #555 0%, #333 100%)`,
          border: `2px solid ${active ? ORANGE : '#555'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, color: '#fff', fontWeight: 900,
          boxShadow: active ? `0 0 16px ${ORANGE}88` : 'none',
          animation: active ? 'ceo-pulse 2s ease-in-out infinite' : 'none',
          transition: 'all 0.5s',
        }}>CEO</div>
        <div style={{ fontSize: 8, color: active ? ORANGE : GREY, letterSpacing: '0.1em' }}>
          {active ? 'ACTIVE' : 'STANDBY'}
        </div>
      </div>

      {/* Status */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 10, color: ORANGE, fontWeight: 700, letterSpacing: '0.15em', marginBottom: 4 }}>
          EXECUTIVE FLOOR — CHIEF ANALYST
        </div>
        <div style={{
          fontSize: 11, color: active ? LIGHT : GREY,
          fontStyle: 'italic',
          transition: 'color 0.3s',
        }}>
          {active ? `"${message}"` : '"Awaiting analysis..."'}
        </div>
      </div>
    </div>
  )
}

// ── Manager office ─────────────────────────────────────────────────────────────

function ManagerOffice({ room, active }: { room: RoomInfo; active: boolean }) {
  const isWriting = room.status === 'active'
  return (
    <div style={{
      width: 110, flexShrink: 0,
      background: `linear-gradient(135deg, #1A0800 0%, #220E00 100%)`,
      border: `1px solid ${active ? ORANGE + '88' : '#333'}`,
      borderRadius: 4,
      padding: '10px 8px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
    }}>
      <div style={{ fontSize: 8, color: ORANGE, fontWeight: 700, letterSpacing: '0.12em', marginBottom: 2 }}>
        MANAGER
      </div>

      {/* Manager figure */}
      <div style={{
        width: 38, height: 38, borderRadius: '50%',
        background: active
          ? `radial-gradient(circle, ${ORANGE} 0%, #994400 100%)`
          : `radial-gradient(circle, #444 0%, #222 100%)`,
        border: `2px solid ${active ? ORANGE : '#444'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 9, color: '#fff', fontWeight: 700,
        boxShadow: active ? `0 0 12px ${ORANGE}66` : 'none',
        animation: isWriting ? 'mgr-write 1.5s ease-in-out infinite' : 'none',
        transition: 'all 0.4s',
      }}>MGR</div>

      <div style={{ fontSize: 8, color: GREY, textAlign: 'center', lineHeight: 1.4 }}>
        {isWriting ? (
          <span style={{ color: ORANGE }}>Writing report...</span>
        ) : active ? (
          <span style={{ color: '#AAA' }}>Reviewing team</span>
        ) : (
          <span>Standby</span>
        )}
      </div>

      {/* Glass wall divider */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0,
        width: 2,
        background: active ? `${ORANGE}44` : '#33333344',
        borderRadius: '2px 0 0 2px',
      }} />
    </div>
  )
}

// ── Task board ────────────────────────────────────────────────────────────────

function TaskBoard({ room }: { room: RoomInfo }) {
  const tasks = room.workers.slice(0, 12)
  if (!tasks.length) return null
  return (
    <div style={{
      background: '#111', border: `1px solid #333`,
      borderRadius: 4, padding: '8px 10px',
      minWidth: 150, flexShrink: 0,
    }}>
      <div style={{ fontSize: 8, color: ORANGE, fontWeight: 700, letterSpacing: '0.12em', marginBottom: 6 }}>
        TASK BOARD
      </div>
      {tasks.map(w => (
        <div key={w.worker_id} style={{
          display: 'flex', alignItems: 'center', gap: 5,
          marginBottom: 3,
        }}>
          <div style={{
            width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
            background: STATUS_COLOR[w.status],
            boxShadow: w.status === 'working' || w.status === 'learning'
              ? `0 0 4px ${STATUS_COLOR[w.status]}` : 'none',
          }} />
          <div style={{
            fontSize: 7.5,
            color: w.status === 'done' ? '#444' : '#BBB',
            textDecoration: w.status === 'done' ? 'line-through' : 'none',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            maxWidth: 110,
          }}>
            {w.task_title}
          </div>
        </div>
      ))}
      {room.workers.length > 12 && (
        <div style={{ fontSize: 7, color: '#555', marginTop: 2 }}>
          +{room.workers.length - 12} more...
        </div>
      )}
    </div>
  )
}

// ── Room floor ────────────────────────────────────────────────────────────────

function RoomFloor({ room }: { room: RoomInfo }) {
  const active = room.status === 'active'
  const complete = room.status === 'complete'
  const progress = room.task_count > 0 ? room.tasks_done / room.task_count : 0
  const statusColor = { idle: '#333', active: ORANGE, complete: '#228833', error: '#CC2222' }[room.status]

  const workersByStatus = {
    learning: room.workers.filter(w => w.status === 'learning'),
    working:  room.workers.filter(w => w.status === 'working'),
    done:     room.workers.filter(w => w.status === 'done'),
    idle:     room.workers.filter(w => w.status === 'idle'),
    stuck:    room.workers.filter(w => w.status === 'stuck'),
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 10,
      background: active ? '#0D0500' : '#0A0A0A',
      border: `2px solid ${statusColor}`,
      borderRadius: 6,
      padding: '12px 16px',
      boxShadow: active ? `inset 0 0 30px ${ORANGE}11, 0 0 20px ${ORANGE}22` : 'none',
      transition: 'all 0.5s',
    }}>

      {/* Room header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
          background: statusColor,
          boxShadow: active ? `0 0 8px ${ORANGE}` : 'none',
          animation: active ? 'dot-pulse 1.5s ease-in-out infinite' : 'none',
        }} />
        <span style={{ fontSize: 14, fontWeight: 700, color: active ? ORANGE : '#888', letterSpacing: '0.15em' }}>
          {room.name.toUpperCase()}
        </span>
        <span style={{ fontSize: 9, color: statusColor, letterSpacing: '0.1em' }}>
          [{room.status.toUpperCase()}]
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 12, fontSize: 9, color: GREY }}>
          {Object.entries(workersByStatus).map(([s, ws]) => ws.length > 0 ? (
            <span key={s} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: STATUS_COLOR[s as WorkerStatus],
                display: 'inline-block',
              }} />
              {ws.length}
            </span>
          ) : null)}
          <span style={{ color: '#555' }}>{room.tasks_done}/{room.task_count}</span>
        </div>
      </div>

      {/* Main office floor */}
      <div style={{
        display: 'flex', gap: 12,
        minHeight: room.workers.length > 0 ? 200 : 80,
      }}>

        {/* Worker desks area */}
        <div style={{
          flex: 1,
          background: `linear-gradient(135deg, #0F0F0F 0%, #141414 100%)`,
          borderRadius: 4,
          padding: '12px 10px',
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* Floor texture */}
          <div style={{
            position: 'absolute', inset: 0,
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
            pointerEvents: 'none',
          }} />

          {room.workers.length === 0 ? (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#333', fontSize: 12, letterSpacing: '0.5em',
            }}>
              AWAITING DEPLOYMENT
            </div>
          ) : (
            /* Worker grid */
            <div style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${Math.min(room.workers.length, 5)}, 1fr)`,
              gap: '12px 8px',
              justifyItems: 'center',
            }}>
              {room.workers.map((w, i) => (
                <WorkerFigure key={w.worker_id} worker={w} index={i} />
              ))}
            </div>
          )}

          {complete && (
            <div style={{
              position: 'absolute', bottom: 8, right: 10,
              fontSize: 10, color: '#228833', fontWeight: 700,
              letterSpacing: '0.15em',
              display: 'flex', alignItems: 'center', gap: 4,
            }}>
              <span style={{ fontSize: 14 }}>✓</span> COMPLETE
            </div>
          )}
        </div>

        {/* Right panel: task board + manager */}
        {room.workers.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <TaskBoard room={room} />
            <div style={{ position: 'relative' }}>
              <ManagerOffice room={room} active={active} />
            </div>
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 8, color: GREY, letterSpacing: '0.12em', minWidth: 55 }}>PROGRESS</span>
        <div style={{ flex: 1, height: 4, background: '#222', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${Math.round(progress * 100)}%`,
            background: complete
              ? '#228833'
              : `linear-gradient(90deg, ${ORANGE} 0%, #FF9933 100%)`,
            borderRadius: 2,
            boxShadow: active && progress > 0 ? `0 0 8px ${ORANGE}88` : 'none',
            transition: 'width 0.6s ease',
          }} />
        </div>
        <span style={{ fontSize: 9, color: active ? ORANGE : GREY, minWidth: 30, textAlign: 'right', fontWeight: 700 }}>
          {Math.round(progress * 100)}%
        </span>
      </div>
    </div>
  )
}

// ── Main OfficeView ────────────────────────────────────────────────────────────

interface OfficeViewProps {
  state: PipelineState
  activeFloor: number
  onFloorChange: (i: number) => void
}

export function OfficeView({ state, activeFloor, onFloorChange }: OfficeViewProps) {
  const ceoMsgRef = useRef("Awaiting dataset...")
  const [ceoMsg, setCeoMsg] = useState("Awaiting dataset...")

  // Auto-switch to active floor
  const roomStatuses = state.rooms.map(r => r.status).join(',')
  useEffect(() => {
    const idx = state.rooms.findIndex(r => r.status === 'active')
    if (idx >= 0) onFloorChange(idx)
  }, [roomStatuses]) // eslint-disable-line react-hooks/exhaustive-deps

  // Track CEO messages
  useEffect(() => {
    const ceoEvents = state.events.filter(e =>
      e.event_type === 'ceo_thinking' || e.event_type === 'ceo_briefed' || e.event_type === 'ceo_done'
    )
    if (ceoEvents.length > 0) {
      const last = ceoEvents[ceoEvents.length - 1] as any
      const msg = last.message || "Analysis in progress..."
      ceoMsgRef.current = msg
      setCeoMsg(msg)
    }
  }, [state.events.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const ceoActive = state.status === 'running'
  const room = state.rooms[activeFloor]

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: '#080808',
      overflow: 'hidden',
      fontFamily: '"Courier New", Courier, monospace',
    }}>

      {/* CEO floor header */}
      <div style={{ padding: '10px 16px 0', flexShrink: 0 }}>
        <CEOFloor active={ceoActive} message={ceoMsg} />
      </div>

      {/* Floor tabs */}
      <div style={{
        display: 'flex',
        background: '#111',
        borderBottom: `2px solid ${ORANGE}44`,
        flexShrink: 0,
        overflowX: 'auto',
        padding: '6px 16px 0',
        gap: 2,
        marginTop: 10,
      }}>
        {state.rooms.map((r, i) => {
          const on = activeFloor === i
          const dot = { idle: '#333', active: ORANGE, complete: '#228833', error: '#CC2222' }[r.status]
          const workerCounts = {
            working: r.workers.filter(w => w.status === 'working').length,
            learning: r.workers.filter(w => w.status === 'learning').length,
          }
          return (
            <button key={r.name} onClick={() => onFloorChange(i)}
              style={{
                padding: '7px 14px 9px',
                border: 'none',
                background: on ? '#1A0A00' : 'transparent',
                color: on ? ORANGE : '#666',
                fontFamily: '"Courier New", monospace',
                fontSize: 10, fontWeight: on ? 700 : 400,
                cursor: 'pointer', letterSpacing: '0.08em',
                display: 'flex', alignItems: 'center', gap: 6,
                whiteSpace: 'nowrap',
                borderBottom: on ? `2px solid ${ORANGE}` : '2px solid transparent',
                borderRadius: '3px 3px 0 0',
                transition: 'all 0.15s',
                position: 'relative',
              }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: dot,
                display: 'inline-block', flexShrink: 0,
                boxShadow: r.status === 'active' ? `0 0 6px ${ORANGE}` : 'none',
                animation: r.status === 'active' ? 'dot-pulse 1.5s infinite' : 'none',
              }} />
              {r.name.toUpperCase()}
              {(workerCounts.working + workerCounts.learning) > 0 && (
                <span style={{
                  fontSize: 8, background: ORANGE, color: '#000',
                  borderRadius: 8, padding: '0 4px', fontWeight: 700,
                }}>
                  {workerCounts.working + workerCounts.learning}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Active room */}
      <div style={{ flex: 1, overflow: 'auto', padding: '12px 16px' }}>
        {room && <RoomFloor room={room} />}
      </div>

      {/* Overall stats footer */}
      <div style={{
        display: 'flex', gap: 20, padding: '6px 16px',
        borderTop: `1px solid #1A1A1A`,
        fontSize: 9, color: GREY, flexShrink: 0,
        background: '#0A0A0A',
      }}>
        <span>ROOMS: {state.rooms.filter(r => r.status === 'complete').length}/{state.rooms.length}</span>
        <span>WORKERS: {state.rooms.reduce((a, r) => a + r.workers.filter(w => w.status === 'done').length, 0)}/{state.rooms.reduce((a, r) => a + r.workers.length, 0)} done</span>
        <span>TASKS: {state.rooms.reduce((a, r) => a + r.tasks_done, 0)}/{state.rooms.reduce((a, r) => a + r.task_count, 0)}</span>
        {state.status === 'running' && (
          <span style={{ color: ORANGE, animation: 'blink 1s step-end infinite' }}>● RUNNING</span>
        )}
        {state.status === 'complete' && (
          <span style={{ color: '#228833' }}>✓ COMPLETE</span>
        )}
      </div>

      <style>{`
        @keyframes w-learn {
          0%, 100% { transform: scale(1) translateY(0); }
          50%       { transform: scale(1.05) translateY(-2px); }
        }
        @keyframes w-work {
          0%, 100% { transform: scale(1); }
          50%       { transform: scale(1.03); }
        }
        @keyframes w-stuck {
          0%, 100% { transform: translateX(0); }
          25%       { transform: translateX(-2px); }
          75%       { transform: translateX(2px); }
        }
        @keyframes ceo-pulse {
          0%, 100% { box-shadow: 0 0 8px ${ORANGE}66; }
          50%       { box-shadow: 0 0 20px ${ORANGE}CC; }
        }
        @keyframes mgr-write {
          0%, 100% { transform: scale(1) rotate(0deg); }
          50%       { transform: scale(1.05) rotate(-3deg); }
        }
        @keyframes dot-pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.4; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
        .w-learn { animation: w-learn 2s ease-in-out infinite; }
        .w-work  { animation: w-work  1.2s ease-in-out infinite; }
        .w-stuck { animation: w-stuck 0.4s ease-in-out infinite; }
      `}</style>
    </div>
  )
}
