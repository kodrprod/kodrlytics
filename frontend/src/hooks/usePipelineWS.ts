import { useState, useCallback, useRef } from 'react'
import type { PipelineEvent, RunCompleteEvent, RoomInfo, WorkerInfo } from '../types'

export interface PipelineState {
  status: 'idle' | 'running' | 'complete' | 'error'
  runId: string | null
  rooms: RoomInfo[]
  events: PipelineEvent[]
  result: RunCompleteEvent | null
  errorMsg: string | null
}

const ROOM_NAMES = ['Intake', 'Extraction', 'Analysis', 'Benchmarking', 'Strategy', 'Reporting']

function makeRooms(): RoomInfo[] {
  return ROOM_NAMES.map((name, i) => ({
    name, stage: i, status: 'idle', workers: [], task_count: 0, tasks_done: 0,
  }))
}

const BACKEND = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL ?? 'http://localhost:8000'
const WS_BACKEND = BACKEND.replace(/^http/, 'ws')

export function usePipelineWS() {
  const [state, setState] = useState<PipelineState>({
    status: 'idle', runId: null,
    rooms: makeRooms(), events: [], result: null, errorMsg: null,
  })
  const wsRef = useRef<WebSocket | null>(null)
  const pendingRef = useRef(false)

  const startRun = useCallback(async (file?: File) => {
    if (pendingRef.current) return
    pendingRef.current = true
    wsRef.current?.close()
    setState(s => ({
      ...s, status: 'running',
      rooms: makeRooms(), events: [], result: null, errorMsg: null,
    }))

    let runId: string
    try {
      const fd = new FormData()
      if (file) fd.append('file', file)
      const res = await fetch(`${BACKEND}/runs-rooms`, {
        method: 'POST',
        body: file ? fd : undefined,
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      runId = data.run_id
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setState(s => ({ ...s, status: 'error', errorMsg: msg }))
      pendingRef.current = false
      return
    }

    setState(s => ({ ...s, runId }))
    const ws = new WebSocket(`${WS_BACKEND}/ws-rooms/${runId}`)
    wsRef.current = ws

    ws.onmessage = (msg) => {
      const event: PipelineEvent = JSON.parse(msg.data)
      setState(s => {
        const events = [...s.events, event]
        let rooms = s.rooms.map(r => ({ ...r, workers: [...r.workers] }))
        let result = s.result
        let status = s.status
        let errorMsg = s.errorMsg

        const et = event.event_type

        if (et === 'room_opened') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = { ...r, status: 'active', task_count: event.task_count, tasks_done: 0, workers: [] }

        } else if (et === 'worker_spawned') {
          const r = rooms[event.stage]
          if (r) {
            const w: WorkerInfo = { worker_id: event.worker_id, task_title: event.task_title, status: 'idle', spawnedAt: Date.now() }
            rooms[event.stage] = { ...r, workers: [...r.workers, w] }
          }

        } else if (et === 'worker_learning') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = { ...r, workers: r.workers.map(w =>
            w.worker_id === event.worker_id
              ? { ...w, status: 'learning' as const, currentAction: event.queries?.[0] ?? 'searching...' }
              : w
          )}

        } else if (et === 'worker_working') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = { ...r, workers: r.workers.map(w =>
            w.worker_id === event.worker_id
              ? { ...w, status: 'working' as const, currentAction: w.task_title, currentRound: 1 }
              : w
          )}

        } else if (et === 'worker_round') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = { ...r, workers: r.workers.map(w =>
            w.worker_id === event.worker_id
              ? { ...w, status: 'working' as const, currentRound: event.round, currentAction: `Round ${event.round}/4: ${w.task_title}` }
              : w
          )}

        } else if (et === 'worker_done') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = {
            ...r,
            workers: r.workers.map(w => w.worker_id === event.worker_id
              ? { ...w, status: 'done' as const, currentAction: '', currentRound: undefined }
              : w
            ),
            tasks_done: r.tasks_done + 1,
          }

        } else if (et === 'room_closed') {
          const r = rooms[event.stage]
          if (r) rooms[event.stage] = {
            ...r, status: 'complete',
            workers: r.workers.map(w => ({ ...w, status: 'done' as const })),
          }

        } else if (et === 'run_complete') {
          result = event
          status = 'complete'
          rooms = rooms.map(r => r.status === 'active'
            ? { ...r, status: 'complete', workers: r.workers.map(w => ({ ...w, status: 'done' as const })) }
            : r)

        } else if (et === 'run_error') {
          status = 'error'
          errorMsg = event.error
        }

        return { ...s, events, rooms, result, status, errorMsg }
      })
    }

    ws.onerror = () => {
      pendingRef.current = false
      setState(s => ({ ...s, status: 'error', errorMsg: 'WebSocket connection failed' }))
    }
    ws.onclose = () => {
      pendingRef.current = false
      setState(s => s.status === 'running' ? { ...s, status: 'complete' } : s)
    }
  }, [])

  return { state, startRun }
}
