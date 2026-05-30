import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface DataPacketProps {
  from: [number, number, number]
  to: [number, number, number]
  startTime: number  // Date.now() when packet was created
  duration?: number  // ms to travel (default 1800)
}

export function DataPacket({ from, to, startTime, duration = 1800 }: DataPacketProps) {
  const meshRef = useRef<THREE.Mesh>(null!)

  const curve = useMemo(() => {
    const mid: [number, number, number] = [
      (from[0] + to[0]) / 2,
      (from[1] + to[1]) / 2 + 0.4,
      (from[2] + to[2]) / 2,
    ]
    return new THREE.CatmullRomCurve3([
      new THREE.Vector3(...from),
      new THREE.Vector3(...mid),
      new THREE.Vector3(...to),
    ])
  }, [from, to])

  useFrame(() => {
    if (!meshRef.current) return
    const t = Math.min((Date.now() - startTime) / duration, 1)
    const pos = curve.getPoint(t)
    meshRef.current.position.copy(pos)
    // Fade out near the end
    const mat = meshRef.current.material as THREE.MeshStandardMaterial
    mat.opacity = t < 0.85 ? 1 : 1 - (t - 0.85) / 0.15
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.1, 8, 8]} />
      <meshStandardMaterial
        color="#00eeff"
        emissive="#00eeff"
        emissiveIntensity={2}
        transparent
        opacity={1}
      />
    </mesh>
  )
}
