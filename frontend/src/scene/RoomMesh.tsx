import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'
import type { RoomInfo, WorkerInfo, WorkerStatus } from '../types'

const ROOM_W = 2.2
const ROOM_H = 1.8
const ROOM_D = 2.0

const STAGE_ACCENT: string[] = [
  '#0088cc',  // 0 Intake       — blue
  '#00aa55',  // 1 Extraction   — green
  '#8844cc',  // 2 Analysis     — purple
  '#cc7700',  // 3 Benchmarking — amber
  '#0055cc',  // 4 Strategy     — deep blue
  '#cc0066',  // 5 Reporting    — magenta
]

const WORKER_COLORS: Record<WorkerStatus, string> = {
  idle:     '#1a2a3a',
  learning: '#0088ff',
  working:  '#00cc66',
  stuck:    '#ff3333',
  done:     '#ffaa00',
}

// Positions inside the room for up to 20 workers
const WORKER_SLOTS: [number, number, number][] = (() => {
  const slots: [number, number, number][] = []
  const cols = 4, rows = 5
  for (let r = 0; r < rows; r++)
    for (let c = 0; c < cols; c++)
      slots.push([
        (c - (cols - 1) / 2) * 0.45,
        -ROOM_H / 2 + 0.22,
        (r - (rows - 1) / 2) * 0.38,
      ])
  return slots
})()

interface WorkerDotProps {
  info: WorkerInfo
  slot: [number, number, number]
  accent: string
}

function WorkerDot({ info, slot, accent }: WorkerDotProps) {
  const ref = useRef<THREE.Mesh>(null!)
  const color = WORKER_COLORS[info.status]
  const targetColor = useMemo(() => new THREE.Color(color), [color])

  useFrame((_, delta) => {
    if (!ref.current) return
    const mat = ref.current.material as THREE.MeshStandardMaterial
    mat.color.lerp(targetColor, delta * 5)
    mat.emissive.lerp(targetColor, delta * 5)

    if (info.status === 'learning') {
      mat.emissiveIntensity = 1.5 + Math.sin(Date.now() * 0.006) * 0.8
    } else if (info.status === 'working') {
      mat.emissiveIntensity = 1.2 + Math.sin(Date.now() * 0.004 + slot[0]) * 0.6
    } else if (info.status === 'stuck') {
      mat.emissiveIntensity = Math.sin(Date.now() * 0.015) > 0 ? 2.5 : 0.2
    } else if (info.status === 'done') {
      mat.emissiveIntensity = 0.8
    } else {
      mat.emissiveIntensity = 0.1
    }
  })

  return (
    <mesh ref={ref} position={slot}>
      <sphereGeometry args={[0.09, 8, 8]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.3}
        metalness={0.3}
        roughness={0.6}
      />
    </mesh>
  )
}

interface RoomMeshProps {
  position: [number, number, number]
  room: RoomInfo
}

export function RoomMesh({ position, room }: RoomMeshProps) {
  const boxRef = useRef<THREE.LineSegments>(null!)
  const managerRef = useRef<THREE.Mesh>(null!)
  const floorRef = useRef<THREE.Mesh>(null!)
  const accent = STAGE_ACCENT[room.stage] ?? '#445566'

  const accentColor  = useMemo(() => new THREE.Color(accent), [accent])
  const dimAccent    = useMemo(() => new THREE.Color(accent).multiplyScalar(0.25), [accent])
  const dimGrey      = useMemo(() => new THREE.Color('#0a1220'), [])
  const activeFloor  = useMemo(() => new THREE.Color(accent).multiplyScalar(0.08), [accent])

  useFrame((_, delta) => {
    // Box wireframe colour
    if (boxRef.current) {
      const mat = boxRef.current.material as THREE.LineBasicMaterial
      const target = room.status === 'active' ? accentColor : room.status === 'complete' ? dimAccent : dimGrey
      mat.color.lerp(target, delta * 3)
    }
    // Manager glow
    if (managerRef.current) {
      const mat = managerRef.current.material as THREE.MeshStandardMaterial
      const intensity = room.status === 'active' ? 2.5 + Math.sin(Date.now() * 0.003) * 0.8 : room.status === 'complete' ? 0.8 : 0.1
      mat.emissiveIntensity += (intensity - mat.emissiveIntensity) * delta * 4
    }
    // Floor colour
    if (floorRef.current) {
      const mat = floorRef.current.material as THREE.MeshBasicMaterial
      const target = room.status === 'active' ? activeFloor : dimGrey
      mat.color.lerp(target, delta * 3)
    }
  })

  const visibleWorkers = room.workers.slice(0, WORKER_SLOTS.length)
  const managerColor = room.status === 'idle' ? '#332200' : '#ffcc44'

  return (
    <group position={position}>
      {/* Wireframe box outline */}
      <lineSegments ref={boxRef}>
        <edgesGeometry args={[new THREE.BoxGeometry(ROOM_W, ROOM_H, ROOM_D)]} />
        <lineBasicMaterial color="#0a1220" />
      </lineSegments>

      {/* Semi-transparent floor */}
      <mesh ref={floorRef} position={[0, -ROOM_H / 2 + 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[ROOM_W - 0.05, ROOM_D - 0.05]} />
        <meshBasicMaterial color="#0a1220" transparent opacity={0.9} />
      </mesh>

      {/* Back wall (subtle) */}
      <mesh position={[0, 0, ROOM_D / 2 - 0.01]}>
        <planeGeometry args={[ROOM_W - 0.05, ROOM_H - 0.05]} />
        <meshBasicMaterial color={accent} transparent opacity={room.status === 'active' ? 0.05 : 0.02} />
      </mesh>

      {/* Manager sphere — front-centre, slightly elevated */}
      <mesh ref={managerRef} position={[0, -ROOM_H / 2 + 0.28, -ROOM_D / 2 + 0.3]}>
        <sphereGeometry args={[0.14, 12, 12]} />
        <meshStandardMaterial
          color={managerColor}
          emissive={managerColor}
          emissiveIntensity={room.status === 'active' ? 2.5 : 0.1}
          metalness={0.8}
          roughness={0.2}
        />
      </mesh>

      {/* Point light when active */}
      {room.status === 'active' && (
        <pointLight color={accent} intensity={1.5} distance={5} position={[0, 0, 0]} />
      )}

      {/* Workers */}
      {visibleWorkers.map((w, i) => (
        <WorkerDot key={w.worker_id} info={w} slot={WORKER_SLOTS[i]} accent={accent} />
      ))}

      {/* Overflow badge */}
      {room.workers.length > WORKER_SLOTS.length && (
        <Html center position={[ROOM_W / 2 - 0.15, -ROOM_H / 2 + 0.15, 0]}>
          <div style={{ color: accent, fontSize: 9, fontWeight: 700, whiteSpace: 'nowrap' }}>
            +{room.workers.length - WORKER_SLOTS.length}
          </div>
        </Html>
      )}

      {/* Room label */}
      <Html center position={[0, ROOM_H / 2 + 0.22, 0]} style={{ pointerEvents: 'none' }}>
        <div style={{
          color: room.status === 'idle' ? '#334455' : room.status === 'complete' ? '#aaddcc' : accent,
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          whiteSpace: 'nowrap',
          textShadow: room.status === 'active' ? `0 0 8px ${accent}` : 'none',
          fontFamily: 'Segoe UI, system-ui, sans-serif',
        }}>
          {room.name}
        </div>
      </Html>

      {/* Task progress badge */}
      {room.task_count > 0 && room.status !== 'idle' && (
        <Html center position={[0, -ROOM_H / 2 - 0.18, 0]} style={{ pointerEvents: 'none' }}>
          <div style={{
            color: room.status === 'complete' ? '#00cc66' : '#446688',
            fontSize: 9,
            letterSpacing: '0.06em',
            fontFamily: 'monospace',
          }}>
            {room.tasks_done}/{room.task_count} tasks
          </div>
        </Html>
      )}
    </group>
  )
}
