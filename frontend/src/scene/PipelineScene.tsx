import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars } from '@react-three/drei'
import { RoomMesh } from './RoomMesh'
import { ConnectionBeam } from './ConnectionBeam'
import { DataPacket } from './DataPacket'
import { FloatingLabel } from './FloatingLabel'
import type { PipelineState } from '../hooks/usePipelineWS'
import { ROOM_POSITIONS } from '../hooks/usePipelineWS'

interface PipelineSceneProps {
  pipelineState: PipelineState
}

export function PipelineScene({ pipelineState }: PipelineSceneProps) {
  const { rooms, packets, labels } = pipelineState

  return (
    <Canvas
      camera={{ position: [0, 3, 13], fov: 60 }}
      style={{ position: 'absolute', inset: 0 }}
      gl={{ antialias: true, alpha: false }}
    >
      {/* Lighting */}
      <ambientLight intensity={0.12} color="#0a1a2e" />
      <directionalLight position={[4, 8, 6]} intensity={0.25} color="#aaddff" />

      {/* Background stars */}
      <Stars radius={80} depth={50} count={3000} factor={3} fade speed={0.4} />

      {/* Thin beams connecting rooms */}
      {ROOM_POSITIONS.slice(0, -1).map((pos, i) => (
        <ConnectionBeam key={i} from={pos} to={ROOM_POSITIONS[i + 1]} />
      ))}

      {/* The 6 team rooms */}
      {rooms.map((room, i) => (
        <RoomMesh key={room.name} position={ROOM_POSITIONS[i]} room={room} />
      ))}

      {/* Data packets flying between rooms */}
      {packets.map(p => (
        <DataPacket key={p.id} from={p.from} to={p.to} startTime={p.ts} duration={1600} />
      ))}

      {/* Floating finding / flag labels */}
      {labels.map(l => {
        const base = ROOM_POSITIONS[l.stage] ?? [0, 0, 0]
        return (
          <FloatingLabel
            key={l.id}
            position={[base[0] + (Math.random() - 0.5) * 1.4, base[1] + 1.3, base[2]]}
            text={l.text}
            kind={l.kind}
            startTime={l.ts}
          />
        )
      })}

      {/* Camera controls */}
      <OrbitControls
        enablePan={false}
        minDistance={6}
        maxDistance={22}
        autoRotate={pipelineState.status === 'idle'}
        autoRotateSpeed={0.25}
        enableDamping
        dampingFactor={0.06}
        target={[0, 0, 0]}
      />
    </Canvas>
  )
}
