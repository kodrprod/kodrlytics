import { useState, useCallback, useRef } from 'react'
import type { PipelineEvent, HubState, StageId, RunCompleteEvent } from '../types'

export interface PipelineState {
  status: 'idle' | 'running' | 'complete' | 'error'
  runId: string | null
  hubStates: Record<StageId, HubState>
  events: PipelineEvent[]
  packets: Array<{ id: string; from: StageId; to: StageId; ts: number }>
  labels: Array<{ id: string; stage: StageId; text: string; kind: 'finding' | 'flag'; ts: number }>
  result: RunCompleteEvent | null
  errorMsg: string | null
}

const INITIAL_HUB_STATES: Record<StageId, HubState> = {
  intake: 'idle', analysis: 'idle', benchmark: 'idle', strategy: 'idle', briefing: 'idle'
}

const BACKEND = 'http://localhost:8000'
const WS_BACKEND = 'ws://localhost:8000'

export function usePipelineWS() {
  const [state, setState] = useState<PipelineState>({
    status: 'idle',
    runId: null,
    hubStates: { ...INITIAL_HUB_STATES },
    events: [],
    packets: [],
    labels: [],
    result: null,
    errorMsg: null,
  })
  const wsRef = useRef<WebSocket | null>(null)

  const startRun = useCallback(async (file?: File) => {
    // Reset
    setState(s => ({
      ...s,
      status: 'running',
      hubStates: { ...INITIAL_HUB_STATES },
      events: [],
      packets: [],
      labels: [],
      result: null,
      errorMsg: null,
    }))

    let runId: string
    try {
      let res: Response
      if (file) {
        const fd = new FormData()
        fd.append('file', file)
        res = await fetch(`${BACKEND}/runs`, { method: 'POST', body: fd })
      } else {
        res = await fetch(`${BACKEND}/runs/sample`, { method: 'POST' })
      }
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      runId = data.run_id
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setState(s => ({ ...s, status: 'error', errorMsg: msg }))
      return
    }

    setState(s => ({ ...s, runId }))

    const ws = new WebSocket(`${WS_BACKEND}/ws/${runId}`)
    wsRef.current = ws

    ws.onmessage = (msg) => {
      const event: PipelineEvent = JSON.parse(msg.data)
      setState(s => {
        const events = [...s.events, event]
        let hubStates = { ...s.hubStates }
        let packets = s.packets.filter(p => Date.now() - p.ts < 2500)
        let labels = s.labels.filter(l => Date.now() - l.ts < 8000)
        let result = s.result
        let status = s.status
        let errorMsg = s.errorMsg

        switch (event.event_type) {
          case 'stage_started':
            hubStates[event.stage] = 'working'
            break
          case 'stage_done':
            if (hubStates[event.stage] !== 'flagged')
              hubStates[event.stage] = 'done'
            break
          case 'data_passed':
            packets = [...packets, { id: `${event.from_stage}-${Date.now()}`, from: event.from_stage, to: event.to_stage, ts: Date.now() }]
            break
          case 'finding_created':
            labels = [...labels, {
              id: event.finding_id + Date.now(),
              stage: event.stage,
              text: `${event.name}: ${event.value?.toFixed(1)} ${event.unit}`,
              kind: 'finding',
              ts: Date.now(),
            }]
            break
          case 'flag_raised':
            hubStates[event.stage] = 'flagged'
            labels = [...labels, {
              id: event.flag_type + Date.now(),
              stage: event.stage,
              text: `⚠ ${event.metric.toUpperCase()}`,
              kind: 'flag',
              ts: Date.now(),
            }]
            break
          case 'run_complete':
            result = event
            status = 'complete'
            break
          case 'run_error':
            hubStates[event.stage as StageId] = 'error'
            status = 'error'
            errorMsg = event.error
            break
        }
        return { ...s, events, hubStates, packets, labels, result, status, errorMsg }
      })
    }

    ws.onerror = () => setState(s => ({ ...s, status: 'error', errorMsg: 'WebSocket connection failed' }))
    ws.onclose = () => {
      setState(s => s.status === 'running' ? { ...s, status: 'complete' } : s)
    }
  }, [])

  return { state, startRun }
}
