import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'

interface FloatingLabelProps {
  position: [number, number, number]
  text: string
  kind: 'finding' | 'flag'
  startTime: number
  lifetime?: number  // ms (default 7000)
}

export function FloatingLabel({ position, text, kind, startTime, lifetime = 7000 }: FloatingLabelProps) {
  const groupRef = useRef<THREE.Group>(null!)

  useFrame(() => {
    if (!groupRef.current) return
    const age = Date.now() - startTime
    const t = Math.min(age / lifetime, 1)
    // Float upward
    groupRef.current.position.y = position[1] + t * 1.2
  })

  const color = kind === 'flag' ? '#ffaa00' : '#00ccff'
  const bg = kind === 'flag' ? 'rgba(80,40,0,0.85)' : 'rgba(0,40,70,0.85)'

  return (
    <group ref={groupRef} position={position}>
      <Html center style={{ pointerEvents: 'none' }}>
        <div style={{
          background: bg,
          border: `1px solid ${color}`,
          borderRadius: '4px',
          padding: '3px 8px',
          fontSize: '10px',
          color,
          fontWeight: 600,
          whiteSpace: 'nowrap',
          textShadow: `0 0 6px ${color}`,
          letterSpacing: '0.05em',
        }}>
          {text}
        </div>
      </Html>
    </group>
  )
}
