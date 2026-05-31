import { useRef, useState, useEffect } from 'react'
import { EventLog } from './EventLog'
import { ResultsPanel } from './ResultsPanel'
import type { PipelineState } from '../hooks/usePipelineWS'

interface HUDProps {
  state: PipelineState
  onStartRun: (file?: File) => void
}

interface JobState {
  job_id: string
  status: string
  filename: string
  company_count: number
  companies_done: number
  current_stage: string
  error: string
  result_ready: boolean
  recent_events: Array<{ event_type: string; company?: string; count?: number }>
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

const API = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL ?? 'http://localhost:8000'

export function HUD({ state, onStartRun }: HUDProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const zipInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [job, setJob] = useState<JobState | null>(null)
  const [jobSubmitting, setJobSubmitting] = useState(false)
  const [jobError, setJobError] = useState('')

  const canRun = state.status === 'idle' || state.status === 'complete' || state.status === 'error'
  const jobActive = job !== null && job.status !== 'complete' && job.status !== 'error'

  // Poll job status every 3 s while active
  useEffect(() => {
    if (!job || !jobActive) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      return
    }
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/jobs/${job.job_id}`)
        if (res.ok) setJob(await res.json())
      } catch { /* ignore transient errors */ }
    }, 3000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [job?.job_id, jobActive])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onStartRun(file)
    e.target.value = ''
  }

  const handleDeepUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setJobSubmitting(true)
    setJobError('')
    setJob(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${API}/jobs`, { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Upload failed')
      }
      const data = await res.json()
      setJob({
        job_id: data.job_id, status: 'queued', filename: file.name,
        company_count: 0, companies_done: 0, current_stage: 'queued',
        error: '', result_ready: false, recent_events: [],
      })
    } catch (err: unknown) {
      setJobError(err instanceof Error ? err.message : String(err))
    } finally {
      setJobSubmitting(false)
    }
  }

  return (
    <div style={{
      position: 'absolute', top: 0, right: 0,
      width: 400, height: '100vh',
      background: 'rgba(5, 12, 22, 0.88)',
      backdropFilter: 'blur(12px)',
      borderLeft: '1px solid rgba(0,120,200,0.2)',
      display: 'flex', flexDirection: 'column',
      padding: '16px', gap: 12, zIndex: 10,
      fontFamily: 'Segoe UI, system-ui, sans-serif',
      overflowY: 'auto',
    }}>
      {/* Header */}
      <div>
        <div style={{ fontSize: 16, fontWeight: 700, color: '#e0eeff', letterSpacing: '0.04em' }}>KODRLYTICS</div>
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
        {state.errorMsg && <span style={{ color: '#ff6666', fontSize: 10 }}>{state.errorMsg.slice(0, 40)}</span>}
      </div>

      {/* Quick run buttons */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={() => onStartRun()} disabled={!canRun} style={btnStyle(canRun, 'blue')}>
          RUN SAMPLE
        </button>
        <button onClick={() => fileInputRef.current?.click()} disabled={!canRun} style={btnStyle(canRun, 'dim')}>
          UPLOAD FILE
        </button>
        <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.pdf,.json"
          style={{ display: 'none' }} onChange={handleFileChange} />
      </div>

      {/* Deep analysis button */}
      <button
        onClick={() => zipInputRef.current?.click()}
        disabled={jobSubmitting || jobActive}
        style={{
          width: '100%', padding: '10px 16px',
          background: jobSubmitting || jobActive ? 'rgba(20,30,40,0.3)' : 'rgba(0,80,40,0.35)',
          border: `1px solid ${jobSubmitting || jobActive ? '#1a2a3a' : '#00aa55'}`,
          borderRadius: 4,
          color: jobSubmitting || jobActive ? '#334455' : '#00ee88',
          fontSize: 12, fontWeight: 700,
          cursor: jobSubmitting || jobActive ? 'not-allowed' : 'pointer',
          letterSpacing: '0.08em',
        }}
      >
        {jobSubmitting ? 'SUBMITTING...' : jobActive ? 'DEEP ANALYSIS RUNNING...' : '⚡ DEEP ANALYSIS (ZIP / LARGE)'}
      </button>
      <input ref={zipInputRef} type="file" accept=".zip,.csv,.xlsx,.pdf,.json"
        style={{ display: 'none' }} onChange={handleDeepUpload} />

      {jobError && (
        <div style={{ color: '#ff6666', fontSize: 10, padding: '4px 8px',
                      background: 'rgba(255,50,50,0.1)', borderRadius: 3 }}>
          {jobError}
        </div>
      )}

      {/* Job status panel */}
      {job && (
        <div style={{
          background: 'rgba(0,30,20,0.4)', border: '1px solid rgba(0,150,80,0.3)',
          borderRadius: 6, padding: '10px 12px', fontSize: 11, color: '#aaccbb',
        }}>
          <div style={{ fontWeight: 700, color: job.status === 'error' ? '#ff6666' : '#00ee88',
                        marginBottom: 6, letterSpacing: '0.06em' }}>
            DEEP JOB — {job.status.toUpperCase()}
          </div>
          <div style={{ color: '#8899aa', marginBottom: 4, fontSize: 10 }}>{job.filename}</div>
          {job.company_count > 0 && (
            <div style={{ marginBottom: 4 }}>
              Companies: {job.companies_done} / {job.company_count}
              <div style={{ marginTop: 3, height: 4, borderRadius: 2,
                            background: 'rgba(0,100,50,0.3)', overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${Math.round((job.companies_done / job.company_count) * 100)}%`,
                  background: '#00ee88', transition: 'width 0.4s',
                }} />
              </div>
            </div>
          )}
          {job.current_stage && (
            <div style={{ color: '#556677', fontSize: 9, marginBottom: 4 }}>
              {job.current_stage.replace(/_/g, ' ')}
            </div>
          )}
          {job.error && <div style={{ color: '#ff6666', fontSize: 10, marginBottom: 4 }}>{job.error}</div>}

          {job.result_ready && (
            <button
              onClick={() => window.open(`${API}/jobs/${job.job_id}/report`, '_blank')}
              style={{
                marginTop: 6, width: '100%', padding: '8px',
                background: 'rgba(0,100,180,0.4)', border: '1px solid #0088ff',
                borderRadius: 4, color: '#66ccff', fontSize: 11, fontWeight: 700,
                cursor: 'pointer', letterSpacing: '0.06em',
              }}
            >
              ↓ DOWNLOAD PDF REPORT
            </button>
          )}

          {job.recent_events.length > 0 && (
            <div style={{ marginTop: 6, maxHeight: 72, overflowY: 'auto' }}>
              {job.recent_events.slice(-6).map((ev, i) => (
                <div key={i} style={{ color: '#445566', fontSize: 9, fontFamily: 'monospace', lineHeight: 1.4 }}>
                  {ev.event_type}{ev.company ? `: ${ev.company}` : ''}{ev.count != null ? ` (${ev.count})` : ''}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Divider */}
      <div style={{ height: 1, background: 'rgba(0,80,160,0.2)' }} />

      {/* Event log or results */}
      {state.result ? <ResultsPanel result={state.result} /> : <EventLog events={state.events} />}

      {/* Footer */}
      <div style={{ fontSize: 9, color: '#223344', textAlign: 'center', letterSpacing: '0.05em' }}>
        ALL PROJECTIONS ARE ILLUSTRATIVE — NOT GUARANTEES
      </div>

      <style>{`@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: 0.3 } }`}</style>
    </div>
  )
}

function btnStyle(active: boolean, variant: 'blue' | 'dim'): React.CSSProperties {
  const colors = {
    blue: { bg: 'rgba(0,100,180,0.3)', border: '#0066aa', text: '#00aaff' },
    dim:  { bg: 'rgba(0,60,100,0.2)',  border: '#004466', text: '#6699bb' },
  }
  const c = colors[variant]
  return {
    flex: 1, padding: '8px 12px',
    background: active ? c.bg : 'rgba(30,40,50,0.3)',
    border: `1px solid ${active ? c.border : '#223344'}`,
    borderRadius: 4,
    color: active ? c.text : '#445566',
    fontSize: 11, fontWeight: 600,
    cursor: active ? 'pointer' : 'not-allowed',
    letterSpacing: '0.06em',
  }
}
