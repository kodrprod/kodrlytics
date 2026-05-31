import { useRef } from 'react'
import { EventLog } from './EventLog'
import { ResultsPanel } from './ResultsPanel'
import type { PipelineState } from '../hooks/usePipelineWS'

const BACKEND = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL ?? 'http://localhost:8000'

const ORANGE = '#FF5500'
const GREEN  = '#1A9940'
const BORDER = '#E0E0E0'
const BG     = '#F7F8FA'
const TEXT   = '#1A1A1A'
const MUTED  = '#888888'

interface HUDProps {
  state: PipelineState
  onStartRun: (file?: File) => void
}

export function HUD({ state, onStartRun }: HUDProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const canRun = state.status === 'idle' || state.status === 'complete' || state.status === 'error'

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onStartRun(file)
    e.target.value = ''
  }

  const statusColor = { idle: MUTED, running: ORANGE, complete: GREEN, error: '#CC2222' }[state.status]
  const statusLabel = { idle: 'Ready', running: 'Running', complete: 'Complete', error: 'Error' }[state.status]

  const activeWorkers = state.rooms.reduce(
    (a, r) => a + r.workers.filter(w => w.status === 'working' || w.status === 'learning').length, 0
  )
  const totalWorkers = state.rooms.reduce((a, r) => a + r.workers.length, 0)
  const tasksDone    = state.rooms.reduce((a, r) => a + r.tasks_done, 0)
  const tasksTotal   = state.rooms.reduce((a, r) => a + r.task_count, 0)

  return (
    <div style={{
      width: 300, flexShrink: 0,
      height: '100vh',
      background: '#FFFFFF',
      borderRight: `2px solid ${BORDER}`,
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
      fontFamily: 'Arial, sans-serif',
    }}>

      {/* Header */}
      <div style={{
        background: '#1A2540',
        padding: '18px 20px',
        borderBottom: `3px solid ${ORANGE}`,
      }}>
        <div style={{ fontSize: 22, fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
          Kodrlytics
        </div>
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)', letterSpacing: '0.15em', marginTop: 3, textTransform: 'uppercase' }}>
          Financial Intelligence System
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 14 }}>

        {/* Status chip */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 14px',
          background: BG,
          border: `1.5px solid ${BORDER}`,
          borderRadius: 8,
        }}>
          <div style={{
            width: 9, height: 9, borderRadius: '50%',
            background: statusColor, flexShrink: 0,
            boxShadow: state.status === 'running' ? `0 0 0 3px ${ORANGE}33` : 'none',
            animation: state.status === 'running' ? 'pulse 1.2s ease-in-out infinite' : 'none',
          }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: statusColor }}>
            {statusLabel}
          </span>
          {state.errorMsg && (
            <span style={{ fontSize: 11, color: '#CC2222', marginLeft: 4 }}>
              {state.errorMsg.slice(0, 28)}
            </span>
          )}
        </div>

        {/* Live counters grid */}
        {state.status === 'running' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[
              { label: 'Active', value: activeWorkers, color: ORANGE },
              { label: 'Total', value: totalWorkers, color: MUTED },
              { label: 'Done', value: tasksDone, color: GREEN },
              { label: 'Tasks', value: tasksTotal, color: '#AAAAAA' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{
                background: BG, border: `1px solid ${BORDER}`,
                borderRadius: 8, padding: '10px 12px',
              }}>
                <div style={{ fontSize: 10, color: MUTED, marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Department progress */}
        {state.status === 'running' && (
          <div>
            <div style={sectionLabel}>Departments</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {state.rooms.map((r) => {
                const prog = r.task_count > 0 ? r.tasks_done / r.task_count : 0
                const col  = { idle: '#DDDDDD', active: ORANGE, complete: GREEN, error: '#CC2222' }[r.status]
                return (
                  <div key={r.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 7, height: 7, borderRadius: '50%', flexShrink: 0, background: col }} />
                    <span style={{ fontSize: 12, color: TEXT, minWidth: 82 }}>{r.name}</span>
                    <div style={{ flex: 1, height: 4, background: '#EEEEEE', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', width: `${Math.round(prog * 100)}%`,
                        background: col, transition: 'width 0.5s',
                      }} />
                    </div>
                    <span style={{ fontSize: 11, color: MUTED, minWidth: 26, textAlign: 'right' }}>
                      {Math.round(prog * 100)}%
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        <div style={{ borderTop: `1px solid ${BORDER}` }} />

        {/* Launch controls */}
        <div>
          <div style={sectionLabel}>Launch Analysis</div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <button onClick={() => onStartRun()} disabled={!canRun} style={btnStyle(canRun, 'primary')}>
              Run Sample
            </button>
            <button onClick={() => fileInputRef.current?.click()} disabled={!canRun} style={btnStyle(canRun, 'secondary')}>
              Upload File
            </button>
          </div>
          <div style={{ fontSize: 11, color: '#AAAAAA' }}>
            Accepts PDF, Excel, CSV, JSON, ZIP
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.pdf,.json,.zip"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
        </div>

        <div style={{ borderTop: `1px solid ${BORDER}` }} />

        {/* Download buttons */}
        {state.status === 'complete' && state.runId && (
          <div>
            <div style={sectionLabel}>Download Report</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <a
                href={`${BACKEND}/reports/${state.runId}.pdf`}
                target="_blank" rel="noopener noreferrer"
                style={dlStyle}
              >
                PDF
              </a>
              <a
                href={`${BACKEND}/reports/${state.runId}.docx`}
                target="_blank" rel="noopener noreferrer"
                style={dlStyle}
              >
                Word
              </a>
            </div>
          </div>
        )}

        {/* Results / log */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <div style={sectionLabel}>{state.result ? 'Results' : 'Live Log'}</div>
          <div style={{ height: 280, overflow: 'auto', background: BG, borderRadius: 8, border: `1px solid ${BORDER}`, padding: 10 }}>
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
        borderTop: `1px solid ${BORDER}`, padding: '8px 16px',
        fontSize: 10, color: '#BBBBBB', textAlign: 'center',
        background: BG,
      }}>
        All projections are illustrative — not investment advice
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
      `}</style>
    </div>
  )
}

const sectionLabel: React.CSSProperties = {
  fontSize: 10, fontWeight: 700, color: MUTED,
  letterSpacing: '0.12em', marginBottom: 8,
  textTransform: 'uppercase',
  fontFamily: 'Arial, sans-serif',
}

function btnStyle(active: boolean, variant: 'primary' | 'secondary'): React.CSSProperties {
  return {
    flex: 1, padding: '10px 12px',
    background: active ? (variant === 'primary' ? ORANGE : '#FFFFFF') : '#F5F5F5',
    border: `1.5px solid ${active ? (variant === 'primary' ? ORANGE : BORDER) : '#E5E5E5'}`,
    color: active ? (variant === 'primary' ? '#FFFFFF' : TEXT) : '#AAAAAA',
    fontFamily: 'Arial, sans-serif',
    fontSize: 12, fontWeight: 700,
    cursor: active ? 'pointer' : 'not-allowed',
    borderRadius: 7,
    transition: 'all 0.15s',
  }
}

const dlStyle: React.CSSProperties = {
  flex: 1, padding: '10px 12px',
  background: '#F0FAF4',
  border: `1.5px solid ${GREEN}`,
  color: GREEN,
  fontFamily: 'Arial, sans-serif',
  fontSize: 12, fontWeight: 700,
  cursor: 'pointer',
  borderRadius: 7,
  textDecoration: 'none',
  textAlign: 'center',
  display: 'block',
  transition: 'all 0.15s',
}
