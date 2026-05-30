export type StageId = 'intake' | 'analysis' | 'benchmark' | 'strategy' | 'briefing'
export type HubState = 'idle' | 'working' | 'done' | 'flagged' | 'error'
export type Severity = 'warning' | 'critical'

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

export type PipelineEvent =
  | StageStartedEvent
  | DataPassedEvent
  | FindingCreatedEvent
  | FlagRaisedEvent
  | StageDoneEvent
  | RunErrorEvent
  | RunCompleteEvent
