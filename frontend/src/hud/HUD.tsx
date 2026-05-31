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

const ACCENT = '#FF6600'
const BLACK  = '#111111'
const GREY   = '#888888'

const API = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL ?? 'http://localhost:8000'

export function HUD({ state, onStartRun }: HUDProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const zipInputRef  = useRef<HTMLInputElement>(null)
  const pollRef      = useRef<ReturnType<typeof setInterval> | null>(null)

  const [job, setJob]               = useState<JobState | null>(null)
  const [jobSubmitting, setJobSubmitting] = useState(false)
  const [jobError, setJobError]     = useState('')

  const canRun   = state.status === 'idle' || state.status === 'complete' || state.status === 'error'
  const jobActive = job !== null && job.status !== 'complete' && job.status !== 'error'

  useEffect(() => {
    if (!job || !jobActive) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      return
    }
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/jobs/${job.job_id}`)
        if (res.ok) setJob(await res.json())
      } catch { /* ignore */ }
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
    setJobSubmitting(true); setJobError(''); setJob(null)
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

  const statusDot = { idle: GREY, running: ACCENT, complete: '#009933', error: '#CC0000' }[state.status]
  const statusLabel = { idle: 'READY', running: 'RUNNING', complete: 'COMPLETE', error: 'ERROR' }[state.status]

  return (
    <div style={{
      width: 320, flexShrink: 0,
      height: '100vh',
      background: '#FFFFFF',
      borderRight: `2px solid ${BLACK}`,
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
      fontFamily: '"Courier New", Courier, monospace',
    }}>

      {/* Header */}
      <div style={{ background: BLACK, padding: '12px 16px', borderBottom: `3px solid ${ACCENT}` }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: '#FFFFFF', letterSpacing: '0.1em' }}>
          KODRLYTICS
        </div>
        <div style={{ fontSize: 9, color: '#666666', letterSpacing: '0.2em', marginTop: 2 }}>
          FINANCIAL ANALYSIS ENGINE
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 9, height: 9, borderRadius: '50%',
            background: statusDot, display: 'inline-block', flexShrink: 0,
            boxShadow: state.status === 'running' ? `0 0 8px ${ACCENT}` : 'none',
            animation: state.status === 'running' ? 'dotPulse 1s infinite' : 'none',
          }} />
          <span style={{ fontSize: 11, fontWeight: 700, color: statusDot, letterSpacing: '0.12em' }}>
            {statusLabel}
          </span>
          {state.errorMsg && (
            <span style={{ fontSize: 9, color: '#CC0000', marginLeft: 4 }}>
              {state.errorMsg.slice(0, 32)}
            </span>
          )}
        </div>

        {/* Section: Quick Run */}
        <div>
          <div style={sectionHeader}>QUICK RUN</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => onStartRun()} disabled={!canRun}
              style={btn(canRun, 'primary')}>
              RUN SAMPLE
            </button>
            <button onClick={() => fileInputRef.current?.click()} disabled={!canRun}
              style={btn(canRun, 'secondary')}>
              UPLOAD FILE
            </button>
          </div>
          <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.pdf,.json"
            style={{ display: 'none' }} onChange={handleFileChange} />
        </div>

        {/* Section: Deep Analysis */}
        <div>
          <div style={sectionHeader}>DEEP ANALYSIS</div>
          <button
            onClick={() => zipInputRef.current?.click()}
            disabled={jobSubmitting || jobActive}
            style={{
              width: '100%', padding: '9px 12px',
              background: jobSubmitting || jobActive ? '#F5F5F5' : '#FFFFFF',
              border: `2px solid ${jobSubmitting || jobActive ? '#CCCCCC' : ACCENT}`,
              color: jobSubmitting || jobActive ? '#AAAAAA' : ACCENT,
              fontFamily: '"Courier New", monospace', fontSize: 11, fontWeight: 700,
              cursor: jobSubmitting || jobActive ? 'not-allowed' : 'pointer',
              letterSpacing: '0.08em',
              transition: 'all 0.2s',
            }}>
            {jobSubmitting ? 'SUBMITTING...' : jobActive ? 'JOB RUNNING...' : '>> DEEP ANALYSIS (ZIP/LARGE)'}
          </button>
          <input ref={zipInputRef} type="file" accept=".zip,.csv,.xlsx,.pdf,.json"
            style={{ display: 'none' }} onChange={handleDeepUpload} />

          {jobError && (
            <div style={{ marginTop: 6, fontSize: 9, color: '#CC0000', padding: '4px 6px', border: '1px solid #CC0000' }}>
              ERR: {jobError}
            </div>
          )}
        </div>

        {/* Job status panel */}
        {job && (
          <div style={{ border: `1px solid ${job.status === 'error' ? '#CC0000' : job.status === 'complete' ? '#009933' : ACCENT}`, padding: '8px 10px' }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', marginBottom: 5,
              color: job.status === 'error' ? '#CC0000' : job.status === 'complete' ? '#009933' : ACCENT }}>
              [JOB: {job.status.toUpperCase()}]
            </div>
            <div style={{ fontSize: 9, color: GREY, marginBottom: 4 }}>{job.filename}</div>

            {job.company_count > 0 && (
              <div style={{ marginBottom: 5 }}>
                <div style={{ fontSize: 9, color: BLACK, marginBottom: 3 }}>
                  Companies: {job.companies_done}/{job.company_count}
                </div>
                <div style={{ height: 4, background: '#E0E0E0', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.round((job.companies_done / job.company_count) * 100)}%`,
                    background: ACCENT, transition: 'width 0.4s',
                  }} />
                </div>
              </div>
            )}

            {job.current_stage && (
              <div style={{ fontSize: 8, color: GREY, marginBottom: 4 }}>
                {job.current_stage.replace(/_/g, ' ').toUpperCase()}
              </div>
            )}
            {job.error && (
              <div style={{ fontSize: 9, color: '#CC0000', marginBottom: 4 }}>{job.error}</div>
            )}

            {job.result_ready && (
              <button
                onClick={() => window.open(`${API}/jobs/${job.job_id}/report`, '_blank')}
                style={{
                  width: '100%', padding: '7px', marginTop: 4,
                  background: BLACK, border: 'none',
                  color: '#FFFFFF', fontSize: 10, fontWeight: 700,
                  fontFamily: '"Courier New", monospace',
                  cursor: 'pointer', letterSpacing: '0.08em',
                }}>
                {'>> DOWNLOAD PDF REPORT'}
              </button>
            )}

            {job.recent_events.length > 0 && (
              <div style={{ marginTop: 6, borderTop: '1px solid #E0E0E0', paddingTop: 5 }}>
                {job.recent_events.slice(-5).map((ev, i) => (
                  <div key={i} style={{ fontSize: 8, color: GREY, lineHeight: 1.5 }}>
                    {ev.event_type}{ev.company ? `: ${ev.company}` : ''}{ev.count != null ? ` (${ev.count})` : ''}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Divider */}
        <div style={{ borderTop: `1px solid #E0E0E0`, paddingTop: 8 }}>
          <div style={sectionHeader}>EVENT LOG</div>
        </div>

        {/* Log or results */}
        <div style={{ flex: 1, minHeight: 0 }}>
          {state.result ? <ResultsPanel result={state.result} /> : <EventLog events={state.events} />}
        </div>

      </div>

      {/* Footer */}
      <div style={{
        borderTop: `1px solid #E0E0E0`, padding: '6px 14px',
        fontSize: 7.5, color: '#BBBBBB', letterSpacing: '0.06em',
        textAlign: 'center',
      }}>
        ALL PROJECTIONS ARE ILLUSTRATIVE -- NOT GUARANTEES
      </div>

      <style>{`
        @keyframes dotPulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
      `}</style>
    </div>
  )
}

const sectionHeader: React.CSSProperties = {
  fontSize: 8, fontWeight: 700, color: GREY, letterSpacing: '0.2em',
  marginBottom: 6, textTransform: 'uppercase',
}

function btn(active: boolean, variant: 'primary' | 'secondary'): React.CSSProperties {
  const isPrimary = variant === 'primary'
  return {
    flex: 1, padding: '8px 10px',
    background: active ? (isPrimary ? BLACK : '#FFFFFF') : '#F5F5F5',
    border: `2px solid ${active ? (isPrimary ? BLACK : '#AAAAAA') : '#E0E0E0'}`,
    color: active ? (isPrimary ? '#FFFFFF' : BLACK) : '#AAAAAA',
    fontFamily: '"Courier New", monospace',
    fontSize: 10, fontWeight: 700,
    cursor: active ? 'pointer' : 'not-allowed',
    letterSpacing: '0.06em',
    transition: 'all 0.15s',
  }
}
