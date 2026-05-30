import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars } from '@react-three/drei'
import { Hub } from './Hub'
import { ConnectionBeam } from './ConnectionBeam'
import { DataPacket } from './DataPacket'
import { FloatingLabel } from './FloatingLabel'
import type { PipelineState } from '../hooks/usePipelineWS'
import type { StageId } from '../types'

const STAGES: StageId[] = ['intake', 'analysis', 'benchmark', 'strategy', 'briefing']
const STAGE_LABELS = ['Intake', 'Analysis', 'Benchmark', 'Strategy', 'Briefing']

// Positions: arc along X, slight Y variation for depth
const HUB_POSITIONS: [number, number, number][] = [
  [-5.0,  0.2, 0],
  [-2.5, -0.2, 0],
  [ 0.0,  0.3, 0],
  [ 2.5, -0.2, 0],
  [ 5.0,  0.2, 0],
]

function getHubPosition(stage: StageId): [number, number, number] {
  const idx = STAGES.indexOf(stage)
  return idx >= 0 ? HUB_POSITIONS[idx] : [0, 0, 0]
}

interface PipelineSceneProps {
  pipelineState: PipelineState
}

export function PipelineScene({ pipelineState }: PipelineSceneProps) {
  const { hubStates, packets, labels } = pipelineState

  return (
    <Canvas
      camera={{ position: [0, 2, 10], fov: 55 }}
      style={{ position: 'absolute', inset: 0 }}
      gl={{ antialias: true, alpha: false }}
    >
      {/* Lighting */}
      <ambientLight intensity={0.15} color="#0a1a2e" />
      <directionalLight position={[5, 10, 5]} intensity={0.3} color="#aaddff" />

      {/* Background stars */}
      <Stars radius={80} depth={50} count={3000} factor={3} fade speed={0.5} />

      {/* Connection beams between hubs */}
      {HUB_POSITIONS.slice(0, -1).map((pos, i) => (
        <ConnectionBeam key={i} from={pos} to={HUB_POSITIONS[i + 1]} />
      ))}

      {/* Hub nodes */}
      {STAGES.map((stage, i) => (
        <Hub
          key={stage}
          position={HUB_POSITIONS[i]}
          state={hubStates[stage]}
          stageIndex={i}
          label={STAGE_LABELS[i]}
        />
      ))}

      {/* Data packets in flight */}
      {packets.map(p => {
        const fromPos = getHubPosition(p.from)
        const toPos = getHubPosition(p.to)
        return (
          <DataPacket
            key={p.id}
            from={fromPos}
            to={toPos}
            startTime={p.ts}
            duration={1800}
          />
        )
      })}

      {/* Floating labels */}
      {labels.map(l => {
        const hubPos = getHubPosition(l.stage)
        const offset: [number, number, number] = [
          hubPos[0] + (Math.random() - 0.5) * 0.8,
          hubPos[1] + 0.7,
          hubPos[2],
        ]
        return (
          <FloatingLabel
            key={l.id}
            position={offset}
            text={l.text}
            kind={l.kind}
            startTime={l.ts}
          />
        )
      })}

      {/* Camera controls */}
      <OrbitControls
        enablePan={false}
        minDistance={5}
        maxDistance={20}
        autoRotate={pipelineState.status === 'idle'}
        autoRotateSpeed={0.3}
        enableDamping
        dampingFactor={0.05}
      />
    </Canvas>
  )
}
