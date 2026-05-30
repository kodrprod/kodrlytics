import { useRef } from 'react'
import { EventLog } from './EventLog'
import { ResultsPanel } from './ResultsPanel'
import type { PipelineState } from '../hooks/usePipelineWS'

interface HUDProps {
  state: PipelineState
  onStartRun: (file?: File) => void
}

const STATUS_COLORS = {
  idle:     '#334455',
  running:  '#00ccff',
  complete: '#00ff88',
  error:    '#ff4444',
}

const STATUS_LABELS = {
  idle:     'READY',
  running:  'RUNNING',
  complete: 'COMPLETE',
  error:    'ERROR',
}

export function HUD({ state, onStartRun }: HUDProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onStartRun(file)
  }

  const canRun = state.status === 'idle' || state.status === 'complete' || state.status === 'error'

  return (
    <div style={{
      position: 'absolute',
      top: 0, right: 0,
      width: 380,
      height: '100vh',
      background: 'rgba(5, 12, 22, 0.88)',
      backdropFilter: 'blur(12px)',
      borderLeft: '1px solid rgba(0,120,200,0.2)',
      display: 'flex',
      flexDirection: 'column',
      padding: '16px',
      gap: 12,
      zIndex: 10,
      fontFamily: 'Segoe UI, system-ui, sans-serif',
    }}>
      {/* Header */}
      <div>
        <div style={{ fontSize: 16, fontWeight: 700, color: '#e0eeff', letterSpacing: '0.04em' }}>
          KODRLYTICS
        </div>
        <div style={{ fontSize: 10, color: '#445566', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Financial Analysis Engine
        </div>
      </div>

      {/* Status indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: STATUS_COLORS[state.status],
          boxShadow: `0 0 6px ${STATUS_COLORS[state.status]}`,
          animation: state.status === 'running' ? 'pulse 1s infinite' : 'none',
        }} />
        <span style={{ color: STATUS_COLORS[state.status], fontSize: 11, fontWeight: 700, letterSpacing: '0.1em' }}>
          {STATUS_LABELS[state.status]}
        </span>
        {state.errorMsg && (
          <span style={{ color: '#ff6666', fontSize: 10 }}>{state.errorMsg.slice(0, 40)}</span>
        )}
      </div>

      {/* Run controls */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button
          onClick={() => onStartRun()}
          disabled={!canRun}
          style={{
            flex: 1,
            padding: '8px 12px',
            background: canRun ? 'rgba(0, 100, 180, 0.3)' : 'rgba(30,40,50,0.3)',
            border: `1px solid ${canRun ? '#0066aa' : '#223344'}`,
            borderRadius: 4,
            color: canRun ? '#00aaff' : '#445566',
            fontSize: 11,
            fontWeight: 600,
            cursor: canRun ? 'pointer' : 'not-allowed',
            letterSpacing: '0.06em',
          }}
        >
          RUN SAMPLE
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={!canRun}
          style={{
            flex: 1,
            padding: '8px 12px',
            background: canRun ? 'rgba(0, 60, 100, 0.2)' : 'rgba(20,30,40,0.2)',
            border: `1px solid ${canRun ? '#004466' : '#1a2a3a'}`,
            borderRadius: 4,
            color: canRun ? '#6699bb' : '#334455',
            fontSize: 11,
            fontWeight: 600,
            cursor: canRun ? 'pointer' : 'not-allowed',
            letterSpacing: '0.06em',
          }}
        >
          UPLOAD FILE
        </button>
        <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.pdf" style={{ display: 'none' }} onChange={handleFileChange} />
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'rgba(0,80,160,0.2)' }} />

      {/* Event log or results */}
      {state.result ? (
        <ResultsPanel result={state.result} />
      ) : (
        <EventLog events={state.events} />
      )}

      {/* Footer */}
      <div style={{ fontSize: 9, color: '#223344', textAlign: 'center', letterSpacing: '0.05em' }}>
        ALL PROJECTIONS ARE ILLUSTRATIVE — NOT GUARANTEES
      </div>

      <style>{`
        @keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: 0.3 } }
      `}</style>
    </div>
  )
}
