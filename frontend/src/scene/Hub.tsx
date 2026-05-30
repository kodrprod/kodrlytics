import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'
import type { HubState } from '../types'

const STATE_COLORS: Record<HubState, string> = {
  idle:    '#1a2a3a',
  working: '#00ccff',
  done:    '#00ff88',
  flagged: '#ffaa00',
  error:   '#ff3333',
}

const STATE_EMISSIVE: Record<HubState, string> = {
  idle:    '#0a1520',
  working: '#0066aa',
  done:    '#006633',
  flagged: '#885500',
  error:   '#880000',
}

interface HubProps {
  position: [number, number, number]
  state: HubState
  stageIndex: number
  label: string
}

export function Hub({ position, state, stageIndex, label }: HubProps) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const lightRef = useRef<THREE.PointLight>(null!)

  const targetColor = new THREE.Color(STATE_COLORS[state])
  const targetEmissive = new THREE.Color(STATE_EMISSIVE[state])

  useFrame((_, delta) => {
    if (!meshRef.current) return
    const mat = meshRef.current.material as THREE.MeshStandardMaterial
    mat.color.lerp(targetColor, delta * 3)
    mat.emissive.lerp(targetEmissive, delta * 3)

    // Idle: gentle float animation
    if (state === 'idle') {
      meshRef.current.position.y = position[1] + Math.sin(Date.now() * 0.001 + stageIndex) * 0.08
    } else if (state === 'working') {
      // Pulse scale
      const pulse = 1 + Math.sin(Date.now() * 0.005) * 0.06
      meshRef.current.scale.setScalar(pulse)
    } else {
      meshRef.current.scale.lerp(new THREE.Vector3(1, 1, 1), delta * 4)
    }

    // Light intensity
    if (lightRef.current) {
      const targetIntensity = state === 'idle' ? 0.5 : state === 'working' ? 3 : 2
      lightRef.current.intensity += (targetIntensity - lightRef.current.intensity) * delta * 4
    }
  })

  const color = STATE_COLORS[state]

  return (
    <group position={position}>
      {/* Core sphere */}
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[0.45, 2]} />
        <meshStandardMaterial
          color={STATE_COLORS[state]}
          emissive={STATE_EMISSIVE[state]}
          emissiveIntensity={1}
          metalness={0.6}
          roughness={0.3}
        />
      </mesh>

      {/* Outer ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.62, 0.025, 8, 48]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
      </mesh>

      {/* Glow light */}
      <pointLight ref={lightRef} color={color} intensity={0.5} distance={4} />

      {/* Label */}
      <Html center position={[0, -0.85, 0]} style={{ pointerEvents: 'none' }}>
        <div style={{
          color: '#aaccee',
          fontSize: '11px',
          fontWeight: 600,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          whiteSpace: 'nowrap',
          textShadow: `0 0 8px ${color}`,
        }}>
          {label}
        </div>
      </Html>
    </group>
  )
}
