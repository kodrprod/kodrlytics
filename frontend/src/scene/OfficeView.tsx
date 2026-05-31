import { useState, useEffect } from 'react'
import type { PipelineState } from '../hooks/usePipelineWS'
import type { WorkerInfo, WorkerStatus, RoomInfo } from '../types'

const ORANGE  = '#FF6600'
const DARK    = '#1A1A1A'
const MID     = '#2D2D2D'
const LIGHT   = '#F0F0F0'
const GREY    = '#888888'
const GREEN   = '#22AA44'
const BLUE    = '#2266EE'

const STATUS_COLOR: Record<WorkerStatus, string> = {
  idle:     '#444444',
  learning: BLUE,
  working:  ORANGE,
  stuck:    '#CC2222',
  done:     GREEN,
}

const STATUS_LABEL: Record<WorkerStatus, string> = {
  idle:     'IDLE',
  learning: 'SEARCH',
  working:  'WORK',
  stuck:    'STUCK',
  done:     'DONE',
}

// ── Speech Bubble ─────────────────────────────────────────────────────────────

function SpeechBubble({ text, color }: { text: string; color: string }) {
  if (!text) return null
  return (
    <div style={{
      position: 'absolute',
      bottom: 'calc(100% + 8px)',
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 30,
      pointerEvents: 'none',
      animation: 'bubble-in 0.18s ease-out',
    }}>
      {/* Bubble body */}
      <div style={{
        background: '#0A0A0A',
        border: `1px solid ${color}`,
        borderRadius: 3,
        padding: '4px 8px',
        fontSize: 9,
        color: '#DDDDDD',
        whiteSpace: 'nowrap',
        maxWidth: 150,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        fontFamily: '"Courier New", monospace',
        boxShadow: `0 0 10px ${color}55, inset 0 0 6px ${color}11`,
        lineHeight: 1.4,
      }}>
        <span style={{ color: color, marginRight: 3 }}>
          {color === BLUE ? '🔍' : '▶'}
        </span>
        {text}
      </div>
      {/* Triangle pointer */}
      <div style={{
        width: 0, height: 0,
        borderLeft: '5px solid transparent',
        borderRight: '5px solid transparent',
        borderTop: `5px solid ${color}`,
        margin: '0 auto',
      }} />
    </div>
  )
}

// ── Low-Poly Worker Figure ────────────────────────────────────────────────────

function WorkerFigure({ worker, index }: { worker: WorkerInfo; index: number }) {
  const color   = STATUS_COLOR[worker.status]
  const label   = worker.worker_id.replace(/\D/g, '').slice(-2).padStart(2, '0') || String(index + 1).padStart(2, '0')
  const isActive = worker.status === 'learning' || worker.status === 'working'
  const isDone   = worker.status === 'done'

  const bubbleText = isActive ? (worker.currentAction || (worker.status === 'learning' ? 'searching...' : worker.task_title)) : ''

  return (
    <div
      title={`${worker.worker_id}: ${worker.task_title} [${worker.status}]`}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 2, userSelect: 'none', position: 'relative',
        filter: isDone ? 'grayscale(0.55)' : 'none',
        opacity: worker.status === 'idle' ? 0.45 : 1,
        transition: 'opacity 0.3s, filter 0.3s',
        animation: isActive ? (worker.status === 'learning' ? 'w-learn 2s ease-in-out infinite' : 'w-work 1.4s ease-in-out infinite') : 'none',
      }}
    >
      {/* Speech bubble — appears above */}
      {bubbleText && <SpeechBubble text={bubbleText} color={color} />}

      {/* ── Monitor (low-poly with hard 3D shadow) ── */}
      <div style={{
        width: 38, height: 26,
        background: isActive ? '#091620' : '#222',
        border: `1.5px solid ${isActive ? color : '#3A3A3A'}`,
        position: 'relative',
        boxShadow: isActive
          ? `3px 3px 0 #000, 0 0 14px ${color}44`
          : '3px 3px 0 #000',
        transition: 'all 0.3s',
        flexShrink: 0,
      }}>
        {/* Screen */}
        <div style={{
          position: 'absolute', top: 2, left: 2, right: 2, bottom: 2,
          background: isActive ? '#040E18' : '#111',
          overflow: 'hidden',
        }}>
          {worker.status === 'working' && (
            <div style={{ padding: '3px 3px', display: 'flex', flexDirection: 'column', gap: 2 }}>
              {[18, 26, 14, 22, 10].map((w, i) => (
                <div key={i} style={{
                  height: 2, width: w, background: ORANGE,
                  borderRadius: 1, opacity: 0.7 - i * 0.1,
                }} />
              ))}
            </div>
          )}
          {worker.status === 'learning' && (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{
                width: 11, height: 11, borderRadius: '50%',
                border: `2px solid ${BLUE}`,
                borderTopColor: 'transparent',
                animation: 'spin 0.7s linear infinite',
              }} />
            </div>
          )}
          {isDone && (
            <div style={{
              height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: GREEN, fontSize: 12, fontWeight: 700,
            }}>✓</div>
          )}
          {worker.status === 'idle' && (
            <div style={{
              height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#333', fontSize: 7, letterSpacing: '0.1em',
            }}>---</div>
          )}
        </div>
        {/* Monitor stand */}
        <div style={{
          position: 'absolute', bottom: -5, left: '50%',
          transform: 'translateX(-50%)',
          width: 11, height: 5, background: '#2A2A2A',
          boxShadow: '2px 2px 0 #111',
        }} />
        {/* 3D right edge */}
        <div style={{
          position: 'absolute', top: 2, right: -3, bottom: -3,
          width: 3, background: '#111', transform: 'skewY(-5deg)',
        }} />
        {/* 3D bottom edge */}
        <div style={{
          position: 'absolute', bottom: -3, left: 2, right: -3,
          height: 3, background: '#0A0A0A',
        }} />
      </div>

      {/* ── Desk (isometric style) ── */}
      <div style={{
        width: 50, height: 6,
        background: '#6B4820',
        boxShadow: '3px 3px 0 #2D1A08',
        marginTop: 3, flexShrink: 0,
        clipPath: 'polygon(0% 0%, 100% 0%, 96% 100%, 4% 100%)',
      }} />

      {/* ── Body — low-poly trapezoid ── */}
      <div style={{
        width: 20, height: 12,
        background: color,
        clipPath: 'polygon(10% 0%, 90% 0%, 100% 100%, 0% 100%)',
        opacity: isDone ? 0.6 : 0.9,
        boxShadow: isActive ? `0 0 8px ${color}66` : 'none',
        transition: 'box-shadow 0.3s',
        flexShrink: 0,
      }} />

      {/* ── Head — hexagonal low-poly ── */}
      <div style={{
        width: 18, height: 18,
        background: isActive ? color : `${color}BB`,
        clipPath: 'polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 7, color: '#fff', fontWeight: 700,
        boxShadow: isActive ? `0 0 10px ${color}88` : 'none',
        transition: 'all 0.3s',
        flexShrink: 0,
        letterSpacing: '0',
      }}>{label}</div>

      {/* ── Status badge ── */}
      <div style={{
        fontSize: 8, color, fontWeight: 700,
        letterSpacing: '0.06em',
        padding: '1px 4px',
        background: `${color}18`,
        border: `0.5px solid ${color}55`,
        lineHeight: 1.3,
      }}>
        {STATUS_LABEL[worker.status]}
        {worker.currentRound && worker.status === 'working' ? ` R${worker.currentRound}` : ''}
      </div>
    </div>
  )
}

// ── CEO Floor ─────────────────────────────────────────────────────────────────

function CEOFloor({ active, message }: { active: boolean; message: string }) {
  return (
    <div style={{
      background: active ? '#150800' : '#0D0D0D',
      border: `2px solid ${active ? ORANGE : '#2A2A2A'}`,
      borderRadius: 5,
      padding: '10px 18px',
      display: 'flex', alignItems: 'center', gap: 18,
      boxShadow: active ? `0 0 24px ${ORANGE}33` : 'none',
      transition: 'all 0.6s',
      flexShrink: 0,
    }}>
      {/* CEO avatar — low-poly diamond */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, flexShrink: 0 }}>
        <div style={{
          width: 44, height: 44,
          background: active
            ? `linear-gradient(135deg, ${ORANGE} 0%, #994400 100%)`
            : '#2A2A2A',
          clipPath: 'polygon(50% 0%, 100% 30%, 100% 70%, 50% 100%, 0% 70%, 0% 30%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, color: '#fff', fontWeight: 900,
          boxShadow: active ? `0 0 20px ${ORANGE}88` : 'none',
          animation: active ? 'ceo-pulse 2s ease-in-out infinite' : 'none',
          transition: 'all 0.5s',
          letterSpacing: '0.05em',
        }}>CEO</div>
        <div style={{ fontSize: 9, color: active ? ORANGE : '#444', letterSpacing: '0.15em', fontWeight: 700 }}>
          {active ? 'ACTIVE' : 'STANDBY'}
        </div>
      </div>

      {/* Message area */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11, color: '#555', fontWeight: 700, letterSpacing: '0.2em', marginBottom: 6 }}>
          EXECUTIVE FLOOR — CHIEF ANALYST
        </div>
        <div style={{
          fontSize: 13, color: active ? '#EEE' : '#555',
          fontStyle: 'italic', lineHeight: 1.5,
          transition: 'color 0.4s',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {active ? `"${message}"` : '"Awaiting dataset..."'}
        </div>
      </div>

      {/* ASCII art corner decoration */}
      <div style={{ fontSize: 18, color: active ? `${ORANGE}55` : '#222', fontWeight: 700, flexShrink: 0, lineHeight: 1 }}>
        {'╔╗\n╚╝'}
      </div>
    </div>
  )
}

// ── Manager Office ────────────────────────────────────────────────────────────

function ManagerOffice({ room, active }: { room: RoomInfo; active: boolean }) {
  const isWriting = room.status === 'active'
  const progress = room.task_count > 0 ? room.tasks_done / room.task_count : 0

  return (
    <div style={{
      width: 120, flexShrink: 0,
      background: '#0D0800',
      border: `1px solid ${active ? ORANGE + '66' : '#2A2A2A'}`,
      borderRadius: 4,
      padding: '10px 10px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 7,
    }}>
      <div style={{ fontSize: 9, color: ORANGE, fontWeight: 700, letterSpacing: '0.15em' }}>
        MANAGER
      </div>

      {/* Manager avatar — low-poly diamond */}
      <div style={{
        width: 46, height: 46,
        background: active
          ? `linear-gradient(135deg, ${ORANGE} 0%, #884400 100%)`
          : '#252525',
        clipPath: 'polygon(50% 0%, 100% 30%, 100% 70%, 50% 100%, 0% 70%, 0% 30%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 10, color: '#fff', fontWeight: 700,
        boxShadow: active ? `0 0 14px ${ORANGE}55` : 'none',
        animation: isWriting ? 'mgr-write 1.8s ease-in-out infinite' : 'none',
        transition: 'all 0.4s',
        letterSpacing: '0.05em',
      }}>MGR</div>

      <div style={{ fontSize: 9, color: active ? '#CCC' : '#444', textAlign: 'center', lineHeight: 1.5 }}>
        {isWriting ? (
          <span style={{ color: ORANGE }}>Writing report…</span>
        ) : active ? (
          <span>Reviewing team</span>
        ) : (
          <span style={{ color: '#333' }}>Standby</span>
        )}
      </div>

      {/* Mini progress ring as ASCII */}
      <div style={{ fontSize: 9, color: '#555', fontFamily: '"Courier New", monospace', textAlign: 'center', lineHeight: 1.3 }}>
        {`[${Math.round(progress * 10) > 0 ? '█'.repeat(Math.min(Math.round(progress * 5), 5)) + '░'.repeat(5 - Math.min(Math.round(progress * 5), 5)) : '░░░░░'}]`}
        <br />
        <span style={{ color: active ? ORANGE : '#333', fontSize: 8 }}>
          {room.tasks_done}/{room.task_count}
        </span>
      </div>
    </div>
  )
}

// ── Task Board ────────────────────────────────────────────────────────────────

function TaskBoard({ room }: { room: RoomInfo }) {
  if (!room.workers.length) return null
  const done = room.workers.filter(w => w.status === 'done').length
  return (
    <div style={{
      background: '#0A0A0A', border: '1px solid #252525',
      borderRadius: 3, padding: '8px 10px',
      minWidth: 170, flexShrink: 0,
      display: 'flex', flexDirection: 'column', flex: 1,
    }}>
      <div style={{
        fontSize: 9, color: ORANGE, fontWeight: 700, letterSpacing: '0.15em',
        marginBottom: 6, display: 'flex', justifyContent: 'space-between',
      }}>
        <span>TASK BOARD</span>
        <span style={{ color: done === room.workers.length ? GREEN : '#666' }}>
          {done}/{room.workers.length}
        </span>
      </div>
      <div style={{ overflowY: 'auto', maxHeight: 300 }}>
        {room.workers.map(w => (
          <div key={w.worker_id} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            marginBottom: 3, padding: '1px 0',
            borderBottom: '1px solid #111',
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
              background: STATUS_COLOR[w.status],
              boxShadow: (w.status === 'working' || w.status === 'learning')
                ? `0 0 5px ${STATUS_COLOR[w.status]}` : 'none',
            }} />
            <div style={{
              fontSize: 9,
              color: w.status === 'done' ? '#3A3A3A'
                : w.status === 'idle' ? '#444'
                : '#CCC',
              textDecoration: w.status === 'done' ? 'line-through' : 'none',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              flex: 1,
            }}>
              {w.task_title}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Room Floor ────────────────────────────────────────────────────────────────

function RoomFloor({ room }: { room: RoomInfo }) {
  const active   = room.status === 'active'
  const complete = room.status === 'complete'
  const progress = room.task_count > 0 ? room.tasks_done / room.task_count : 0
  const statusColor = { idle: '#333', active: ORANGE, complete: GREEN, error: '#CC2222' }[room.status]

  const workersByStatus = {
    learning: room.workers.filter(w => w.status === 'learning').length,
    working:  room.workers.filter(w => w.status === 'working').length,
    done:     room.workers.filter(w => w.status === 'done').length,
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 12,
      background: active ? '#0A0400' : '#090909',
      border: `2px solid ${statusColor}`,
      borderRadius: 6,
      padding: '14px 18px',
      boxShadow: active ? `inset 0 0 40px ${ORANGE}0D, 0 0 24px ${ORANGE}22` : 'none',
      transition: 'all 0.5s',
    }}>

      {/* Room header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <div style={{
          width: 10, height: 10, flexShrink: 0,
          background: statusColor,
          clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
          boxShadow: active ? `0 0 10px ${ORANGE}` : 'none',
          animation: active ? 'dot-pulse 1.5s ease-in-out infinite' : 'none',
        }} />
        <span style={{ fontSize: 18, fontWeight: 700, color: active ? ORANGE : '#777', letterSpacing: '0.15em' }}>
          {room.name.toUpperCase()}
        </span>
        <span style={{
          fontSize: 10, color: statusColor, letterSpacing: '0.12em',
          border: `1px solid ${statusColor}44`, padding: '1px 6px',
        }}>
          {room.status.toUpperCase()}
        </span>

        {/* Live worker counts */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 14, fontSize: 10, color: GREY }}>
          {workersByStatus.learning > 0 && (
            <span style={{ color: BLUE, display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: 9 }}>SEARCH</span>
              <span style={{ fontWeight: 700, fontSize: 13 }}>{workersByStatus.learning}</span>
            </span>
          )}
          {workersByStatus.working > 0 && (
            <span style={{ color: ORANGE, display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: 9 }}>WORK</span>
              <span style={{ fontWeight: 700, fontSize: 13 }}>{workersByStatus.working}</span>
            </span>
          )}
          {workersByStatus.done > 0 && (
            <span style={{ color: GREEN, display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: 9 }}>DONE</span>
              <span style={{ fontWeight: 700, fontSize: 13 }}>{workersByStatus.done}</span>
            </span>
          )}
          <span style={{ color: '#444', fontSize: 10 }}>{room.tasks_done}/{room.task_count}</span>
        </div>
      </div>

      {/* Main floor area */}
      <div style={{ display: 'flex', gap: 14, minHeight: room.workers.length > 15 ? 360 : room.workers.length > 0 ? 220 : 90 }}>

        {/* Worker desks — overflow visible so bubbles float up */}
        <div style={{
          flex: 1,
          background: '#0D0D0D',
          border: '1px solid #1A1A1A',
          borderRadius: 4,
          padding: '36px 14px 14px',   // extra top padding for speech bubbles
          position: 'relative',
          overflow: 'visible',
        }}>
          {/* Floor tile grid texture */}
          <div style={{
            position: 'absolute', inset: 0, borderRadius: 4,
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.012) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.012) 1px, transparent 1px)
            `,
            backgroundSize: '48px 48px',
            pointerEvents: 'none',
            overflow: 'hidden',
          }} />

          {/* Room number watermark */}
          <div style={{
            position: 'absolute', right: 10, bottom: 8,
            fontSize: 48, fontWeight: 700, color: '#FFFFFF08',
            letterSpacing: '-0.05em', pointerEvents: 'none', userSelect: 'none',
            lineHeight: 1,
          }}>
            {room.stage + 1}
          </div>

          {room.workers.length === 0 ? (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#282828', fontSize: 13, letterSpacing: '0.5em',
            }}>
              AWAITING DEPLOYMENT
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${
                room.workers.length <= 4 ? room.workers.length :
                room.workers.length <= 12 ? 4 : 5
              }, 1fr)`,
              gap: '28px 14px',
              justifyItems: 'center',
              position: 'relative',
            }}>
              {room.workers.map((w, i) => (
                <WorkerFigure key={w.worker_id} worker={w} index={i} />
              ))}
            </div>
          )}

          {complete && (
            <div style={{
              position: 'absolute', bottom: 8, right: 12,
              fontSize: 11, color: GREEN, fontWeight: 700,
              letterSpacing: '0.15em',
              display: 'flex', alignItems: 'center', gap: 5,
              background: '#001A08', padding: '3px 8px',
              border: `1px solid ${GREEN}44`,
            }}>
              <span style={{ fontSize: 14 }}>✓</span> ANALYSIS COMPLETE
            </div>
          )}
        </div>

        {/* Right panel: task board + manager */}
        {room.workers.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: 170, flexShrink: 0 }}>
            <TaskBoard room={room} />
            <ManagerOffice room={room} active={active} />
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <span style={{ fontSize: 10, color: '#555', letterSpacing: '0.15em', minWidth: 68 }}>PROGRESS</span>
        <div style={{ flex: 1, height: 5, background: '#1A1A1A', borderRadius: 1, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${Math.round(progress * 100)}%`,
            background: complete
              ? GREEN
              : `linear-gradient(90deg, ${ORANGE} 0%, #FF9933 100%)`,
            boxShadow: active && progress > 0 ? `0 0 10px ${ORANGE}88` : 'none',
            transition: 'width 0.7s ease',
          }} />
        </div>
        <span style={{
          fontSize: 11, color: active ? ORANGE : complete ? GREEN : '#555',
          minWidth: 36, textAlign: 'right', fontWeight: 700,
        }}>
          {Math.round(progress * 100)}%
        </span>
      </div>
    </div>
  )
}

// ── Main OfficeView ───────────────────────────────────────────────────────────

interface OfficeViewProps {
  state: PipelineState
  activeFloor: number
  onFloorChange: (i: number) => void
}

export function OfficeView({ state, activeFloor, onFloorChange }: OfficeViewProps) {
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
      const last = ceoEvents[ceoEvents.length - 1] as { message?: string }
      setCeoMsg(last.message || "Analysis in progress...")
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
      <div style={{ padding: '12px 18px 0', flexShrink: 0 }}>
        <CEOFloor active={ceoActive} message={ceoMsg} />
      </div>

      {/* Floor navigation tabs */}
      <div style={{
        display: 'flex',
        background: '#0D0D0D',
        borderBottom: `2px solid ${ORANGE}44`,
        flexShrink: 0,
        overflowX: 'auto',
        padding: '8px 18px 0',
        gap: 3,
        marginTop: 12,
      }}>
        {state.rooms.map((r, i) => {
          const on   = activeFloor === i
          const dot  = { idle: '#2A2A2A', active: ORANGE, complete: GREEN, error: '#CC2222' }[r.status]
          const busy = r.workers.filter(w => w.status === 'working' || w.status === 'learning').length
          return (
            <button key={r.name} onClick={() => onFloorChange(i)}
              style={{
                padding: '8px 16px 10px',
                border: 'none',
                background: on ? '#170A00' : 'transparent',
                color: on ? ORANGE : '#555',
                fontFamily: '"Courier New", monospace',
                fontSize: 12, fontWeight: on ? 700 : 400,
                cursor: 'pointer', letterSpacing: '0.1em',
                display: 'flex', alignItems: 'center', gap: 7,
                whiteSpace: 'nowrap',
                borderBottom: on ? `2px solid ${ORANGE}` : '2px solid transparent',
                borderRadius: '3px 3px 0 0',
                transition: 'all 0.15s',
              }}>
              <span style={{
                width: 7, height: 7,
                background: dot,
                clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
                display: 'inline-block', flexShrink: 0,
                boxShadow: r.status === 'active' ? `0 0 6px ${ORANGE}` : 'none',
                animation: r.status === 'active' ? 'dot-pulse 1.5s infinite' : 'none',
              }} />
              {r.name.toUpperCase()}
              {busy > 0 && (
                <span style={{
                  fontSize: 9, background: ORANGE, color: '#000',
                  borderRadius: 10, padding: '0 5px', fontWeight: 700, lineHeight: '14px',
                }}>{busy}</span>
              )}
            </button>
          )
        })}
      </div>

      {/* Active room view */}
      <div style={{ flex: 1, overflow: 'auto', padding: '14px 18px' }}>
        {room && <RoomFloor room={room} />}
      </div>

      {/* Footer stats bar */}
      <div style={{
        display: 'flex', gap: 24, padding: '6px 18px',
        borderTop: `1px solid #181818`,
        fontSize: 11, color: '#444', flexShrink: 0,
        background: '#080808',
        letterSpacing: '0.08em',
      }}>
        <span>ROOMS {state.rooms.filter(r => r.status === 'complete').length}/{state.rooms.length}</span>
        <span>WORKERS {state.rooms.reduce((a, r) => a + r.workers.filter(w => w.status === 'done').length, 0)}/{state.rooms.reduce((a, r) => a + r.workers.length, 0)}</span>
        <span>TASKS {state.rooms.reduce((a, r) => a + r.tasks_done, 0)}/{state.rooms.reduce((a, r) => a + r.task_count, 0)}</span>
        {state.status === 'running' && (
          <span style={{ color: ORANGE, marginLeft: 'auto', animation: 'blink 1s step-end infinite', fontWeight: 700 }}>
            ● RUNNING
          </span>
        )}
        {state.status === 'complete' && (
          <span style={{ color: GREEN, marginLeft: 'auto', fontWeight: 700 }}>✓ COMPLETE</span>
        )}
      </div>

      <style>{`
        @keyframes w-learn {
          0%, 100% { transform: scale(1) translateY(0); }
          50%       { transform: scale(1.04) translateY(-3px); }
        }
        @keyframes w-work {
          0%, 100% { transform: scale(1) rotate(0deg); }
          50%       { transform: scale(1.03) rotate(0.5deg); }
        }
        @keyframes ceo-pulse {
          0%, 100% { box-shadow: 0 0 10px ${ORANGE}55; }
          50%       { box-shadow: 0 0 28px ${ORANGE}CC; }
        }
        @keyframes mgr-write {
          0%, 100% { transform: scale(1) rotate(0deg); }
          40%       { transform: scale(1.05) rotate(-4deg); }
          80%       { transform: scale(1.03) rotate(2deg); }
        }
        @keyframes dot-pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.35; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
        @keyframes bubble-in {
          from { opacity: 0; transform: translateX(-50%) translateY(4px); }
          to   { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      `}</style>
    </div>
  )
}
