import { useState, useEffect } from 'react'
import type { PipelineState } from '../hooks/usePipelineWS'
import type { WorkerInfo, WorkerStatus, RoomInfo } from '../types'

const ORANGE  = '#FF5500'
const GREEN   = '#1A9940'
const BLUE    = '#1155CC'
const RED     = '#CC2222'
const GREY    = '#777777'
const BORDER  = '#E0E0E0'
const BG      = '#F7F8FA'
const CARD    = '#FFFFFF'
const TEXT    = '#1A1A1A'
const MUTED   = '#888888'

const STATUS_COLOR: Record<WorkerStatus, string> = {
  idle:     '#CCCCCC',
  learning: BLUE,
  working:  ORANGE,
  stuck:    RED,
  done:     GREEN,
}

const STATUS_LABEL: Record<WorkerStatus, string> = {
  idle:     'Idle',
  learning: 'Searching',
  working:  'Working',
  stuck:    'Stuck',
  done:     'Done',
}

// ── Speech Bubble ─────────────────────────────────────────────────────────────

function SpeechBubble({ text, color }: { text: string; color: string }) {
  if (!text) return null
  return (
    <div style={{
      position: 'absolute',
      bottom: 'calc(100% + 10px)',
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 40,
      pointerEvents: 'none',
      animation: 'bubbleIn 0.15s ease-out',
      minWidth: 120,
      maxWidth: 180,
    }}>
      <div style={{
        background: CARD,
        border: `1.5px solid ${color}`,
        borderRadius: 6,
        padding: '5px 10px',
        fontSize: 11,
        color: TEXT,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        fontFamily: 'Arial, sans-serif',
        boxShadow: `0 2px 12px rgba(0,0,0,0.12)`,
        lineHeight: 1.4,
        textAlign: 'center',
      }}>
        <span style={{ color, fontWeight: 600, marginRight: 4 }}>
          {color === BLUE ? '⌕' : '▸'}
        </span>
        {text.length > 22 ? text.slice(0, 22) + '…' : text}
      </div>
      <div style={{
        width: 0, height: 0,
        borderLeft: '6px solid transparent',
        borderRight: '6px solid transparent',
        borderTop: `6px solid ${color}`,
        margin: '0 auto',
      }} />
    </div>
  )
}

// ── Worker Card ───────────────────────────────────────────────────────────────

function WorkerCard({ worker, index }: { worker: WorkerInfo; index: number }) {
  const color    = STATUS_COLOR[worker.status]
  const label    = worker.worker_id.replace(/\D/g, '').slice(-2).padStart(2, '0')
  const isActive = worker.status === 'learning' || worker.status === 'working'
  const isDone   = worker.status === 'done'
  const bubbleText = isActive
    ? (worker.currentAction || (worker.status === 'learning' ? 'Searching…' : worker.task_title))
    : ''

  return (
    <div
      title={`${worker.worker_id}: ${worker.task_title} [${worker.status}]`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 4,
        position: 'relative',
        opacity: worker.status === 'idle' ? 0.45 : 1,
        transition: 'opacity 0.3s',
        animation: worker.status === 'working' ? 'workerWork 1.6s ease-in-out infinite'
          : worker.status === 'learning' ? 'workerLearn 2s ease-in-out infinite'
          : 'none',
      }}
    >
      {bubbleText && <SpeechBubble text={bubbleText} color={color} />}

      {/* Monitor */}
      <div style={{
        width: 40, height: 28,
        background: isActive ? '#F0F4FF' : '#F5F5F5',
        border: `2px solid ${isActive ? color : BORDER}`,
        borderRadius: 3,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: 2,
        boxShadow: isActive ? `0 0 0 2px ${color}22` : 'none',
        transition: 'all 0.3s',
        position: 'relative',
      }}>
        {worker.status === 'working' && [0,1,2].map(i => (
          <div key={i} style={{
            height: 2, borderRadius: 1,
            width: [22, 16, 10][i],
            background: ORANGE, opacity: 1 - i * 0.25,
          }} />
        ))}
        {worker.status === 'learning' && (
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            border: `2px solid ${BLUE}`,
            borderTopColor: 'transparent',
            animation: 'spin 0.7s linear infinite',
          }} />
        )}
        {isDone && (
          <span style={{ fontSize: 13, color: GREEN }}>✓</span>
        )}
        {worker.status === 'idle' && (
          <span style={{ fontSize: 9, color: '#CCC' }}>_ _</span>
        )}
        {/* stand */}
        <div style={{
          position: 'absolute', bottom: -5, left: '50%',
          transform: 'translateX(-50%)',
          width: 10, height: 5,
          background: BORDER, borderRadius: '0 0 2px 2px',
        }} />
      </div>

      {/* Desk */}
      <div style={{
        width: 52, height: 5,
        background: isActive ? '#E8D5C0' : '#E8E8E8',
        borderRadius: 2,
        marginTop: 2,
      }} />

      {/* Avatar circle */}
      <div style={{
        width: 26, height: 26, borderRadius: '50%',
        background: isDone ? '#EEF5EE' : isActive ? `${color}18` : '#F0F0F0',
        border: `2px solid ${isDone ? GREEN : isActive ? color : BORDER}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 9, fontWeight: 700, color: isDone ? GREEN : isActive ? color : MUTED,
        fontFamily: 'Arial, sans-serif',
        transition: 'all 0.3s',
        boxShadow: isActive ? `0 0 0 3px ${color}22` : 'none',
      }}>{label}</div>

      {/* Status pill */}
      <div style={{
        fontSize: 9, fontWeight: 600,
        color: isDone ? GREEN : isActive ? color : MUTED,
        fontFamily: 'Arial, sans-serif',
        letterSpacing: '0.02em',
        background: isDone ? '#EEF5EE' : isActive ? `${color}12` : '#F5F5F5',
        padding: '1px 6px',
        borderRadius: 10,
        border: `1px solid ${isDone ? GREEN + '44' : isActive ? color + '33' : BORDER}`,
      }}>
        {STATUS_LABEL[worker.status]}
        {worker.currentRound && worker.status === 'working' ? ` · R${worker.currentRound}` : ''}
      </div>
    </div>
  )
}

// ── CEO Bar ───────────────────────────────────────────────────────────────────

function CEOBar({ active, message }: { active: boolean; message: string }) {
  return (
    <div style={{
      background: CARD,
      border: `1.5px solid ${active ? ORANGE : BORDER}`,
      borderRadius: 8,
      padding: '10px 18px',
      display: 'flex', alignItems: 'center', gap: 16,
      boxShadow: active ? `0 2px 16px ${ORANGE}22` : '0 1px 4px rgba(0,0,0,0.06)',
      transition: 'all 0.5s',
    }}>
      {/* CEO avatar */}
      <div style={{
        width: 44, height: 44, borderRadius: '50%',
        background: active ? ORANGE : '#F0F0F0',
        border: `3px solid ${active ? ORANGE : BORDER}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 700,
        color: active ? '#FFF' : MUTED,
        fontFamily: 'Arial, sans-serif',
        boxShadow: active ? `0 0 0 4px ${ORANGE}22` : 'none',
        animation: active ? 'ceoPulse 2s ease-in-out infinite' : 'none',
        transition: 'all 0.4s',
        letterSpacing: '0.03em',
        flexShrink: 0,
      }}>CEO</div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 10, fontWeight: 600, color: MUTED,
          letterSpacing: '0.1em', textTransform: 'uppercase',
          fontFamily: 'Arial, sans-serif', marginBottom: 4,
        }}>
          Chief Analyst — Executive Floor
        </div>
        <div style={{
          fontSize: 14, color: active ? TEXT : MUTED,
          fontFamily: 'Arial, sans-serif',
          fontStyle: 'italic',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          transition: 'color 0.3s',
        }}>
          {active ? `"${message}"` : '"Awaiting dataset…"'}
        </div>
      </div>

      <div style={{
        fontSize: 11, fontWeight: 600,
        color: active ? ORANGE : '#CCC',
        fontFamily: 'Arial, sans-serif',
        letterSpacing: '0.1em',
        background: active ? `${ORANGE}12` : '#F5F5F5',
        padding: '4px 10px', borderRadius: 12,
        border: `1px solid ${active ? ORANGE + '33' : BORDER}`,
      }}>
        {active ? '● ACTIVE' : '○ STANDBY'}
      </div>
    </div>
  )
}

// ── Manager Panel ─────────────────────────────────────────────────────────────

function ManagerPanel({ room, active }: { room: RoomInfo; active: boolean }) {
  const isWriting = room.status === 'active'
  const progress  = room.task_count > 0 ? room.tasks_done / room.task_count : 0

  return (
    <div style={{
      width: 130,
      background: active ? `${ORANGE}08` : '#F9F9F9',
      border: `1.5px solid ${active ? ORANGE + '66' : BORDER}`,
      borderRadius: 8,
      padding: '12px 10px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: MUTED, letterSpacing: '0.1em', fontFamily: 'Arial, sans-serif' }}>
        MANAGER
      </div>

      <div style={{
        width: 48, height: 48, borderRadius: '50%',
        background: active ? ORANGE : '#EEEEEE',
        border: `3px solid ${active ? ORANGE : BORDER}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 700,
        color: active ? '#FFF' : MUTED,
        fontFamily: 'Arial, sans-serif',
        animation: isWriting ? 'mgrWrite 1.8s ease-in-out infinite' : 'none',
        transition: 'all 0.4s',
      }}>MGR</div>

      <div style={{
        fontSize: 11, color: active ? TEXT : MUTED,
        textAlign: 'center', lineHeight: 1.5,
        fontFamily: 'Arial, sans-serif',
      }}>
        {isWriting ? <span style={{ color: ORANGE, fontWeight: 600 }}>Writing report…</span>
          : active ? 'Reviewing team'
          : 'Standby'}
      </div>

      {/* Progress */}
      <div style={{ width: '100%' }}>
        <div style={{
          height: 4, background: BORDER, borderRadius: 2, overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${Math.round(progress * 100)}%`,
            background: room.status === 'complete' ? GREEN : ORANGE,
            borderRadius: 2,
            transition: 'width 0.6s ease',
          }} />
        </div>
        <div style={{
          fontSize: 10, color: MUTED, textAlign: 'center', marginTop: 4,
          fontFamily: 'Arial, sans-serif',
        }}>
          {room.tasks_done} / {room.task_count} tasks
        </div>
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
      background: CARD,
      border: `1.5px solid ${BORDER}`,
      borderRadius: 8,
      padding: '10px 12px',
      minWidth: 175, flex: 1,
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 8,
      }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: MUTED, letterSpacing: '0.1em', fontFamily: 'Arial, sans-serif' }}>
          TASKS
        </span>
        <span style={{
          fontSize: 11, fontWeight: 700,
          color: done === room.workers.length && done > 0 ? GREEN : MUTED,
          fontFamily: 'Arial, sans-serif',
        }}>
          {done}/{room.workers.length}
        </span>
      </div>
      <div style={{ overflowY: 'auto', maxHeight: 300 }}>
        {room.workers.map(w => (
          <div key={w.worker_id} style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '3px 0',
            borderBottom: `1px solid ${BG}`,
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
              background: STATUS_COLOR[w.status],
            }} />
            <div style={{
              fontSize: 11,
              color: w.status === 'done' ? '#BBBBBB'
                : w.status === 'idle' ? '#CCCCCC'
                : TEXT,
              textDecoration: w.status === 'done' ? 'line-through' : 'none',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              flex: 1,
              fontFamily: 'Arial, sans-serif',
            }}>
              {w.task_title}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Room Card ─────────────────────────────────────────────────────────────────

function RoomCard({ room }: { room: RoomInfo }) {
  const active   = room.status === 'active'
  const complete = room.status === 'complete'
  const progress = room.task_count > 0 ? room.tasks_done / room.task_count : 0
  const accent   = active ? ORANGE : complete ? GREEN : BORDER

  const searching = room.workers.filter(w => w.status === 'learning').length
  const working   = room.workers.filter(w => w.status === 'working').length
  const done      = room.workers.filter(w => w.status === 'done').length

  return (
    <div style={{
      background: CARD,
      border: `2px solid ${accent}`,
      borderRadius: 10,
      padding: '16px 20px',
      display: 'flex', flexDirection: 'column', gap: 14,
      boxShadow: active
        ? `0 4px 24px ${ORANGE}18`
        : complete ? `0 2px 12px ${GREEN}12`
        : '0 1px 6px rgba(0,0,0,0.06)',
      transition: 'all 0.4s',
    }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: accent,
          boxShadow: active ? `0 0 0 3px ${ORANGE}33` : 'none',
          animation: active ? 'dotPulse 1.5s ease-in-out infinite' : 'none',
          flexShrink: 0,
        }} />

        <span style={{
          fontSize: 18, fontWeight: 700,
          color: active ? ORANGE : complete ? GREEN : TEXT,
          fontFamily: 'Arial, sans-serif',
          letterSpacing: '-0.01em',
        }}>
          {room.name}
        </span>

        <span style={{
          fontSize: 11, fontWeight: 600,
          color: active ? ORANGE : complete ? GREEN : MUTED,
          background: active ? `${ORANGE}12` : complete ? `${GREEN}12` : BG,
          border: `1px solid ${accent}44`,
          padding: '2px 8px', borderRadius: 10,
          fontFamily: 'Arial, sans-serif',
        }}>
          {room.status.charAt(0).toUpperCase() + room.status.slice(1)}
        </span>

        {/* Live counters */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
          {searching > 0 && (
            <span style={{
              fontSize: 11, fontWeight: 600, color: BLUE,
              background: `${BLUE}10`, padding: '2px 8px', borderRadius: 10,
              fontFamily: 'Arial, sans-serif',
            }}>⌕ {searching} searching</span>
          )}
          {working > 0 && (
            <span style={{
              fontSize: 11, fontWeight: 600, color: ORANGE,
              background: `${ORANGE}10`, padding: '2px 8px', borderRadius: 10,
              fontFamily: 'Arial, sans-serif',
            }}>▸ {working} working</span>
          )}
          {done > 0 && !complete && (
            <span style={{
              fontSize: 11, fontWeight: 600, color: GREEN,
              background: `${GREEN}10`, padding: '2px 8px', borderRadius: 10,
              fontFamily: 'Arial, sans-serif',
            }}>✓ {done} done</span>
          )}
          {complete && (
            <span style={{
              fontSize: 11, fontWeight: 700, color: GREEN,
              background: `${GREEN}12`, padding: '2px 10px', borderRadius: 10,
              fontFamily: 'Arial, sans-serif',
            }}>✓ Complete</span>
          )}
        </div>
      </div>

      {/* Floor */}
      <div style={{
        display: 'flex', gap: 14,
        minHeight: room.workers.length > 15 ? 380 : room.workers.length > 0 ? 240 : 80,
      }}>
        {/* Worker grid */}
        <div style={{
          flex: 1,
          background: BG,
          borderRadius: 6,
          border: `1px solid ${BORDER}`,
          padding: '40px 16px 16px',
          position: 'relative',
          overflow: 'visible',
        }}>
          {room.workers.length === 0 ? (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#CCCCCC', fontSize: 13,
              fontFamily: 'Arial, sans-serif', letterSpacing: '0.05em',
            }}>
              Awaiting deployment…
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${
                room.workers.length <= 4 ? room.workers.length
                  : room.workers.length <= 12 ? 4 : 5
              }, 1fr)`,
              gap: '32px 16px',
              justifyItems: 'center',
              position: 'relative',
            }}>
              {room.workers.map((w, i) => (
                <WorkerCard key={w.worker_id} worker={w} index={i} />
              ))}
            </div>
          )}

          {/* Room number watermark */}
          <div style={{
            position: 'absolute', right: 12, bottom: 8,
            fontSize: 64, fontWeight: 900, color: 'rgba(0,0,0,0.04)',
            pointerEvents: 'none', userSelect: 'none', lineHeight: 1,
            fontFamily: 'Arial, sans-serif',
          }}>{room.stage + 1}</div>
        </div>

        {/* Right panel */}
        {room.workers.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: 175, flexShrink: 0 }}>
            <TaskBoard room={room} />
            <ManagerPanel room={room} active={active} />
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 11, color: MUTED, fontFamily: 'Arial, sans-serif', minWidth: 60 }}>
          Progress
        </span>
        <div style={{
          flex: 1, height: 6,
          background: '#EEEEEE',
          borderRadius: 3, overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${Math.round(progress * 100)}%`,
            background: complete ? GREEN : ORANGE,
            borderRadius: 3,
            transition: 'width 0.7s ease',
          }} />
        </div>
        <span style={{
          fontSize: 12, fontWeight: 700,
          color: active ? ORANGE : complete ? GREEN : MUTED,
          fontFamily: 'Arial, sans-serif', minWidth: 36, textAlign: 'right',
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
  const [ceoMsg, setCeoMsg] = useState('Awaiting dataset…')

  const roomStatuses = state.rooms.map(r => r.status).join(',')
  useEffect(() => {
    const idx = state.rooms.findIndex(r => r.status === 'active')
    if (idx >= 0) onFloorChange(idx)
  }, [roomStatuses]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const ceoEvents = state.events.filter(e =>
      e.event_type === 'ceo_thinking' || e.event_type === 'ceo_briefed' || e.event_type === 'ceo_done'
    )
    if (ceoEvents.length > 0) {
      const last = ceoEvents[ceoEvents.length - 1] as { message?: string }
      setCeoMsg(last.message || 'Analysis in progress…')
    }
  }, [state.events.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const room = state.rooms[activeFloor]

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: BG,
      overflow: 'hidden',
      fontFamily: 'Arial, sans-serif',
    }}>

      {/* CEO bar */}
      <div style={{ padding: '14px 20px 0', flexShrink: 0 }}>
        <CEOBar active={state.status === 'running'} message={ceoMsg} />
      </div>

      {/* Tab navigation */}
      <div style={{
        display: 'flex',
        background: CARD,
        borderBottom: `2px solid ${BORDER}`,
        flexShrink: 0,
        padding: '10px 20px 0',
        gap: 4,
        marginTop: 14,
        boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
      }}>
        {state.rooms.map((r, i) => {
          const on   = activeFloor === i
          const dot  = { idle: '#CCCCCC', active: ORANGE, complete: GREEN, error: RED }[r.status]
          const busy = r.workers.filter(w => w.status === 'working' || w.status === 'learning').length
          return (
            <button key={r.name} onClick={() => onFloorChange(i)}
              style={{
                padding: '8px 16px 10px',
                border: 'none',
                background: 'transparent',
                color: on ? ORANGE : '#888888',
                fontFamily: 'Arial, sans-serif',
                fontSize: 13, fontWeight: on ? 700 : 400,
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 7,
                whiteSpace: 'nowrap',
                borderBottom: on ? `2.5px solid ${ORANGE}` : '2.5px solid transparent',
                transition: 'all 0.15s',
              }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%',
                background: dot, flexShrink: 0,
                display: 'inline-block',
                boxShadow: r.status === 'active' ? `0 0 0 3px ${ORANGE}33` : 'none',
                animation: r.status === 'active' ? 'dotPulse 1.5s infinite' : 'none',
              }} />
              {r.name}
              {busy > 0 && (
                <span style={{
                  fontSize: 10, background: ORANGE, color: '#FFF',
                  borderRadius: 10, padding: '1px 6px', fontWeight: 700,
                }}>{busy}</span>
              )}
            </button>
          )
        })}
      </div>

      {/* Active room */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
        {room && <RoomCard room={room} />}
      </div>

      {/* Footer */}
      <div style={{
        display: 'flex', gap: 24, padding: '8px 20px',
        borderTop: `1px solid ${BORDER}`,
        fontSize: 12, color: MUTED, flexShrink: 0,
        background: CARD,
        fontFamily: 'Arial, sans-serif',
      }}>
        <span>Rooms: <b style={{ color: TEXT }}>{state.rooms.filter(r => r.status === 'complete').length}/{state.rooms.length}</b></span>
        <span>Workers: <b style={{ color: TEXT }}>{state.rooms.reduce((a, r) => a + r.workers.filter(w => w.status === 'done').length, 0)}/{state.rooms.reduce((a, r) => a + r.workers.length, 0)}</b> done</span>
        <span>Tasks: <b style={{ color: TEXT }}>{state.rooms.reduce((a, r) => a + r.tasks_done, 0)}/{state.rooms.reduce((a, r) => a + r.task_count, 0)}</b></span>
        {state.status === 'running' && (
          <span style={{ color: ORANGE, marginLeft: 'auto', fontWeight: 600, animation: 'blink 1.2s step-end infinite' }}>
            ● Running
          </span>
        )}
        {state.status === 'complete' && (
          <span style={{ color: GREEN, marginLeft: 'auto', fontWeight: 700 }}>✓ Analysis Complete</span>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes workerWork { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-3px); } }
        @keyframes workerLearn { 0%,100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        @keyframes ceoPulse { 0%,100% { box-shadow: 0 0 0 4px ${ORANGE}22; } 50% { box-shadow: 0 0 0 8px ${ORANGE}44; } }
        @keyframes mgrWrite { 0%,100% { transform: rotate(0deg); } 40% { transform: rotate(-5deg); } 80% { transform: rotate(3deg); } }
        @keyframes dotPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
        @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes bubbleIn { from { opacity: 0; transform: translateX(-50%) translateY(6px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
      `}</style>
    </div>
  )
}
