import { useState, useCallback, useRef } from 'react'
import type {
  PipelineEvent, HubState, StageId, RunCompleteEvent, RoomInfo, WorkerInfo,
} from '../types'

export interface PipelineState {
  status: 'idle' | 'running' | 'complete' | 'error'
  runId: string | null
  hubStates: Record<StageId, HubState>
  rooms: RoomInfo[]
  events: PipelineEvent[]
  packets: Array<{ id: string; from: [number,number,number]; to: [number,number,number]; ts: number }>
  labels: Array<{ id: string; stage: number; text: string; kind: 'finding' | 'flag'; ts: number }>
  result: RunCompleteEvent | null
  errorMsg: string | null
}

const ROOM_NAMES = ['Intake', 'Extraction', 'Analysis', 'Benchmarking', 'Strategy', 'Reporting']
// Old pipeline stage → room stage index
const STAGE_TO_IDX: Record<StageId, number> = {
  intake: 0, analysis: 2, benchmark: 3, strategy: 4, briefing: 5,
}

function makeRooms(): RoomInfo[] {
  return ROOM_NAMES.map((name, i) => ({
    name, stage: i, status: 'idle', workers: [], task_count: 0, tasks_done: 0,
  }))
}

const INITIAL_HUB_STATES: Record<StageId, HubState> = {
  intake: 'idle', analysis: 'idle', benchmark: 'idle', strategy: 'idle', briefing: 'idle',
}

// Room positions in 3D world (X axis, evenly spread)
export const ROOM_POSITIONS: [number, number, number][] = [
  [-7.5, 0, 0],
  [-4.5, 0, 0],
  [-1.5, 0, 0],
  [ 1.5, 0, 0],
  [ 4.5, 0, 0],
  [ 7.5, 0, 0],
]

const BACKEND = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL ?? 'http://localhost:8000'
const WS_BACKEND = BACKEND.replace(/^http/, 'ws')

export function usePipelineWS() {
  const [state, setState] = useState<PipelineState>({
    status: 'idle',
    runId: null,
    hubStates: { ...INITIAL_HUB_STATES },
    rooms: makeRooms(),
    events: [],
    packets: [],
    labels: [],
    result: null,
    errorMsg: null,
  })
  const wsRef = useRef<WebSocket | null>(null)

  const startRun = useCallback(async (file?: File, useRooms = true) => {
    wsRef.current?.close()
    setState(s => ({
      ...s,
      status: 'running',
      hubStates: { ...INITIAL_HUB_STATES },
      rooms: makeRooms(),
      events: [],
      packets: [],
      labels: [],
      result: null,
      errorMsg: null,
    }))

    // Submit run
    let runId: string
    try {
      let res: Response
      if (useRooms) {
        const fd = new FormData()
        if (file) fd.append('file', file)
        res = await fetch(`${BACKEND}/runs-rooms`, { method: 'POST', body: file ? fd : undefined })
      } else {
        if (file) {
          const fd = new FormData()
          fd.append('file', file)
          res = await fetch(`${BACKEND}/runs`, { method: 'POST', body: fd })
        } else {
          res = await fetch(`${BACKEND}/runs/sample`, { method: 'POST' })
        }
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
    const wsPath = useRooms ? `/ws-rooms/${runId}` : `/ws/${runId}`
    const ws = new WebSocket(`${WS_BACKEND}${wsPath}`)
    wsRef.current = ws

    ws.onmessage = (msg) => {
      const event: PipelineEvent = JSON.parse(msg.data)
      setState(s => {
        const events = [...s.events, event]
        let hubStates = { ...s.hubStates }
        let rooms = s.rooms.map(r => ({ ...r, workers: [...r.workers] }))
        const packets = s.packets.filter(p => Date.now() - p.ts < 2500)
        const labels = s.labels.filter(l => Date.now() - l.ts < 8000)
        let result = s.result
        let status = s.status
        let errorMsg = s.errorMsg

        const et = event.event_type

        // ── Old pipeline events → update room state synthetically ─────────────
        if (et === 'stage_started') {
          const idx = STAGE_TO_IDX[event.stage] ?? -1
          hubStates[event.stage] = 'working'
          if (idx >= 0) {
            rooms[idx] = {
              ...rooms[idx], status: 'active',
              workers: [
                { worker_id: `V${idx+1}-01`, task_title: 'Researching', status: 'learning', spawnedAt: Date.now() },
                { worker_id: `V${idx+1}-02`, task_title: 'Processing',  status: 'working', spawnedAt: Date.now() + 200 },
                { worker_id: `V${idx+1}-03`, task_title: 'Analysing',   status: 'working', spawnedAt: Date.now() + 400 },
              ],
              task_count: 3, tasks_done: 0,
            }
          }
        } else if (et === 'stage_done') {
          const idx = STAGE_TO_IDX[event.stage] ?? -1
          if (hubStates[event.stage] !== 'flagged') hubStates[event.stage] = 'done'
          if (idx >= 0) {
            rooms[idx] = {
              ...rooms[idx], status: 'complete',
              workers: rooms[idx].workers.map(w => ({ ...w, status: 'done' as const })),
              tasks_done: rooms[idx].task_count,
            }
          }
        } else if (et === 'data_passed') {
          const fromIdx = STAGE_TO_IDX[event.from_stage as StageId] ?? 0
          const toIdx   = STAGE_TO_IDX[event.to_stage   as StageId] ?? 1
          packets.push({
            id: `${event.from_stage}-${Date.now()}`,
            from: ROOM_POSITIONS[fromIdx],
            to:   ROOM_POSITIONS[toIdx],
            ts:   Date.now(),
          })
        } else if (et === 'finding_created') {
          const idx = STAGE_TO_IDX[event.stage] ?? 2
          labels.push({
            id: event.finding_id + Date.now(), stage: idx,
            text: `${event.name}: ${event.value?.toFixed(1)} ${event.unit}`,
            kind: 'finding', ts: Date.now(),
          })
        } else if (et === 'flag_raised') {
          const idx = STAGE_TO_IDX[event.stage] ?? 3
          hubStates[event.stage] = 'flagged'
          labels.push({
            id: event.flag_type + Date.now(), stage: idx,
            text: `! ${event.metric.toUpperCase()}`,
            kind: 'flag', ts: Date.now(),
          })

        // ── New room-pipeline events ───────────────────────────────────────────
        } else if (et === 'room_opened') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = { ...r, status: 'active', task_count: event.task_count, tasks_done: 0 }
        } else if (et === 'worker_spawned') {
          const r = rooms[event.stage]
          if (r) {
            const w: WorkerInfo = { worker_id: event.worker_id, task_title: event.task_title, status: 'idle', spawnedAt: Date.now() }
            rooms[event.stage] = { ...r, workers: [...r.workers, w] }
          }
        } else if (et === 'worker_learning') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = { ...r, workers: r.workers.map(w => w.worker_id === event.worker_id ? { ...w, status: 'learning' as const } : w) }
        } else if (et === 'worker_working') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = { ...r, workers: r.workers.map(w => w.worker_id === event.worker_id ? { ...w, status: 'working' as const } : w) }
        } else if (et === 'worker_done') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = { ...r, workers: r.workers.map(w => w.worker_id === event.worker_id ? { ...w, status: 'done' as const } : w), tasks_done: r.tasks_done + 1 }
        } else if (et === 'room_closed') {
          const r = rooms[event.stage]
          if (r) {
            rooms[event.stage] = { ...r, status: 'complete', workers: r.workers.map(w => ({ ...w, status: 'done' as const })) }
            // Send data packet to next room
            if (event.stage < 5) {
              packets.push({ id: `room-${event.stage}-${Date.now()}`, from: ROOM_POSITIONS[event.stage], to: ROOM_POSITIONS[event.stage + 1], ts: Date.now() })
            }
          }

        // ── Terminal events ────────────────────────────────────────────────────
        } else if (et === 'run_complete') {
          result = event
          status = 'complete'
          rooms = rooms.map(r => r.status === 'active' ? { ...r, status: 'complete', workers: r.workers.map(w => ({ ...w, status: 'done' as const })) } : r)
        } else if (et === 'run_error') {
          status = 'error'
          errorMsg = event.error
        }

        return { ...s, events, hubStates, rooms, packets, labels, result, status, errorMsg }
      })
    }

    ws.onerror = () => setState(s => ({ ...s, status: 'error', errorMsg: 'WebSocket connection failed' }))
    ws.onclose = () => setState(s => s.status === 'running' ? { ...s, status: 'complete' } : s)
  }, [])

  return { state, startRun }
}
