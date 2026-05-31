import { useRef } from 'react'
import { EventLog } from './EventLog'
import { ResultsPanel } from './ResultsPanel'
import type { PipelineState } from '../hooks/usePipelineWS'

interface HUDProps {
  state: PipelineState
  onStartRun: (file?: File) => void
}

const ORANGE = '#FF6600'
const DARK   = '#111111'
const GREY   = '#666666'

export function HUD({ state, onStartRun }: HUDProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const canRun = state.status === 'idle' || state.status === 'complete' || state.status === 'error'

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onStartRun(file)
    e.target.value = ''
  }

  const statusDot   = { idle: '#444', running: ORANGE, complete: '#228833', error: '#CC2222' }[state.status]
  const statusLabel = { idle: 'READY', running: 'RUNNING', complete: 'COMPLETE', error: 'ERROR' }[state.status]

  // Count active workers across all rooms
  const activeWorkers = state.rooms.reduce(
    (a, r) => a + r.workers.filter(w => w.status === 'working' || w.status === 'learning').length, 0
  )
  const totalWorkers = state.rooms.reduce((a, r) => a + r.workers.length, 0)
  const tasksDone = state.rooms.reduce((a, r) => a + r.tasks_done, 0)
  const tasksTotal = state.rooms.reduce((a, r) => a + r.task_count, 0)

  return (
    <div style={{
      width: 300, flexShrink: 0,
      height: '100vh',
      background: '#111',
      borderRight: `2px solid #222`,
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
      fontFamily: '"Courier New", Courier, monospace',
    }}>

      {/* Header */}
      <div style={{ background: '#0A0A0A', padding: '14px 16px', borderBottom: `2px solid ${ORANGE}` }}>
        <div style={{ fontSize: 17, fontWeight: 700, color: '#FFF', letterSpacing: '0.12em' }}>
          KODRLYTICS
        </div>
        <div style={{ fontSize: 8, color: '#444', letterSpacing: '0.2em', marginTop: 2 }}>
          FINANCIAL INTELLIGENCE SYSTEM
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* Status */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 10px',
          background: '#0A0A0A',
          border: `1px solid #222`,
          borderRadius: 3,
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: statusDot, flexShrink: 0,
            boxShadow: state.status === 'running' ? `0 0 8px ${ORANGE}` : 'none',
            animation: state.status === 'running' ? 'pulse 1s ease-in-out infinite' : 'none',
          }} />
          <span style={{ fontSize: 11, fontWeight: 700, color: statusDot, letterSpacing: '0.12em' }}>
            {statusLabel}
          </span>
          {state.errorMsg && (
            <span style={{ fontSize: 8, color: '#CC2222', marginLeft: 4 }}>
              {state.errorMsg.slice(0, 28)}
            </span>
          )}
        </div>

        {/* Live counters */}
        {state.status === 'running' && (
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr',
            gap: 6, fontSize: 10,
          }}>
            {[
              { label: 'ACTIVE', value: activeWorkers, color: ORANGE },
              { label: 'TOTAL', value: totalWorkers, color: '#888' },
              { label: 'DONE', value: tasksDone, color: '#228833' },
              { label: 'TASKS', value: tasksTotal, color: '#555' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{
                background: '#0D0D0D', border: '1px solid #222',
                borderRadius: 3, padding: '6px 8px',
                display: 'flex', flexDirection: 'column', gap: 1,
              }}>
                <span style={{ fontSize: 7, color: '#444', letterSpacing: '0.15em' }}>{label}</span>
                <span style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1 }}>{value}</span>
              </div>
            ))}
          </div>
        )}

        {/* Room progress bars */}
        {state.status === 'running' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <div style={{ fontSize: 8, color: '#444', letterSpacing: '0.15em', marginBottom: 2 }}>
              DEPARTMENT STATUS
            </div>
            {state.rooms.map((r) => {
              const prog = r.task_count > 0 ? r.tasks_done / r.task_count : 0
              const col = { idle: '#333', active: ORANGE, complete: '#228833', error: '#CC2222' }[r.status]
              return (
                <div key={r.name} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                    background: col,
                    boxShadow: r.status === 'active' ? `0 0 4px ${ORANGE}` : 'none',
                  }} />
                  <span style={{ fontSize: 8, color: '#666', minWidth: 72 }}>
                    {r.name.slice(0, 10).toUpperCase()}
                  </span>
                  <div style={{ flex: 1, height: 3, background: '#1A1A1A', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', width: `${Math.round(prog * 100)}%`,
                      background: col, transition: 'width 0.5s',
                    }} />
                  </div>
                  <span style={{ fontSize: 8, color: '#444', minWidth: 22, textAlign: 'right' }}>
                    {Math.round(prog * 100)}%
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {/* Divider */}
        <div style={{ borderTop: '1px solid #1A1A1A' }} />

        {/* Launch controls */}
        <div>
          <div style={sectionLabel}>LAUNCH ANALYSIS</div>
          <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
            <button onClick={() => onStartRun()} disabled={!canRun}
              style={btnStyle(canRun, 'primary')}>
              RUN SAMPLE
            </button>
            <button onClick={() => fileInputRef.current?.click()} disabled={!canRun}
              style={btnStyle(canRun, 'secondary')}>
              UPLOAD
            </button>
          </div>
          <div style={{ fontSize: 8, color: '#333', letterSpacing: '0.05em' }}>
            Accepts: PDF, Excel, CSV, JSON, ZIP (company datasets)
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.pdf,.json,.zip"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
        </div>

        <div style={{ borderTop: '1px solid #1A1A1A' }} />

        {/* Event log / results */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <div style={sectionLabel}>
            {state.result ? 'RESULTS' : 'LIVE LOG'}
          </div>
          <div style={{ height: 280, overflow: 'auto' }}>
            {state.result ? (
              <ResultsPanel result={state.result} />
            ) : (
              <EventLog events={state.events} />
            )}
          </div>
        </div>

      </div>

      {/* Footer */}
      <div style={{
        borderTop: '1px solid #1A1A1A', padding: '5px 14px',
        fontSize: 7, color: '#333', letterSpacing: '0.05em', textAlign: 'center',
      }}>
        ALL PROJECTIONS ARE ILLUSTRATIVE -- NOT INVESTMENT ADVICE
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
      `}</style>
    </div>
  )
}

const sectionLabel: React.CSSProperties = {
  fontSize: 8, fontWeight: 700, color: '#444',
  letterSpacing: '0.2em', marginBottom: 7,
}

function btnStyle(active: boolean, variant: 'primary' | 'secondary'): React.CSSProperties {
  return {
    flex: 1, padding: '9px 10px',
    background: active ? (variant === 'primary' ? ORANGE : 'transparent') : '#1A1A1A',
    border: `1.5px solid ${active ? (variant === 'primary' ? ORANGE : '#444') : '#222'}`,
    color: active ? (variant === 'primary' ? '#000' : '#888') : '#333',
    fontFamily: '"Courier New", monospace',
    fontSize: 10, fontWeight: 700,
    cursor: active ? 'pointer' : 'not-allowed',
    letterSpacing: '0.08em',
    transition: 'all 0.15s',
    borderRadius: 2,
  }
}
