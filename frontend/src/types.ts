export type StageId = 'intake' | 'analysis' | 'benchmark' | 'strategy' | 'briefing'
export type HubState = 'idle' | 'working' | 'done' | 'flagged' | 'error'
export type Severity = 'warning' | 'critical'
export type WorkerStatus = 'idle' | 'learning' | 'working' | 'stuck' | 'done'

// ── Room / worker state ────────────────────────────────────────────────────────
export interface WorkerInfo {
  worker_id: string
  task_title: string
  status: WorkerStatus
  spawnedAt: number   // Date.now()
}

export interface RoomInfo {
  name: string
  stage: number
  status: 'idle' | 'active' | 'complete' | 'error'
  workers: WorkerInfo[]
  task_count: number
  tasks_done: number
}

// ── Existing pipeline events ───────────────────────────────────────────────────
export interface BaseEvent {
  run_id: string
  timestamp: string
}

export interface StageStartedEvent extends BaseEvent {
  event_type: 'stage_started'
  stage: StageId
  stage_index: number
}

export interface DataPassedEvent extends BaseEvent {
  event_type: 'data_passed'
  from_stage: StageId
  to_stage: StageId
  summary: string
}

export interface FindingCreatedEvent extends BaseEvent {
  event_type: 'finding_created'
  stage: StageId
  finding_id: string
  name: string
  value: number | null
  unit: string
  period: string
}

export interface FlagRaisedEvent extends BaseEvent {
  event_type: 'flag_raised'
  stage: StageId
  flag_type: string
  severity: Severity
  message: string
  metric: string
}

export interface StageDoneEvent extends BaseEvent {
  event_type: 'stage_done'
  stage: StageId
  stage_index: number
  duration_ms: number
}

export interface RunErrorEvent extends BaseEvent {
  event_type: 'run_error'
  stage: string
  error: string
}

export interface RunCompleteEvent extends BaseEvent {
  event_type: 'run_complete'
  company_name: string
  total_duration_ms: number
  finding_count: number
  flag_count: number
  ratios: Array<{ finding_id: string; name: string; value: number; unit: string; period: string }>
  flags: Array<{ flag_type: string; severity: string; message: string; metric: string }>
  projections: Array<{
    metric: string
    current_value: number
    unit: string
    description: string
    disclaimer: string
    scenarios: Array<{ label: string; target_value: number; impact_eur: number | null; impact_description: string }>
  }>
  narrative: string
}

// ── Room-based pipeline events (from /ws-rooms/{run_id}) ──────────────────────
export interface RoomOpenedEvent extends BaseEvent {
  event_type: 'room_opened'
  room_name: string
  stage: number
  worker_count: number
  task_count: number
}

export interface WorkerSpawnedEvent extends BaseEvent {
  event_type: 'worker_spawned'
  room_name: string
  stage: number
  worker_id: string
  task_title: string
}

export interface WorkerLearningEvent extends BaseEvent {
  event_type: 'worker_learning'
  room_name: string
  stage: number
  worker_id: string
  queries: string[]
}

export interface WorkerWorkingEvent extends BaseEvent {
  event_type: 'worker_working'
  room_name: string
  stage: number
  worker_id: string
  task_title: string
}

export interface WorkerDoneEvent extends BaseEvent {
  event_type: 'worker_done'
  room_name: string
  stage: number
  worker_id: string
  task_title: string
}

export interface ManagerWritingEvent extends BaseEvent {
  event_type: 'manager_writing'
  room_name: string
  stage: number
}

export interface RoomClosedEvent extends BaseEvent {
  event_type: 'room_closed'
  room_name: string
  stage: number
  worker_count: number
}

export type PipelineEvent =
  | StageStartedEvent
  | DataPassedEvent
  | FindingCreatedEvent
  | FlagRaisedEvent
  | StageDoneEvent
  | RunErrorEvent
  | RunCompleteEvent
  | RoomOpenedEvent
  | WorkerSpawnedEvent
  | WorkerLearningEvent
  | WorkerWorkingEvent
  | WorkerDoneEvent
  | ManagerWritingEvent
  | RoomClosedEvent
