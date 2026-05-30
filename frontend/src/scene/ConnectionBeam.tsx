import { useMemo } from 'react'
import { Line } from '@react-three/drei'
import * as THREE from 'three'

interface ConnectionBeamProps {
  from: [number, number, number]
  to: [number, number, number]
}

export function ConnectionBeam({ from, to }: ConnectionBeamProps) {
  const points = useMemo(() => {
    const mid: [number, number, number] = [
      (from[0] + to[0]) / 2,
      (from[1] + to[1]) / 2 + 0.4,
      (from[2] + to[2]) / 2,
    ]
    return new THREE.CatmullRomCurve3([
      new THREE.Vector3(...from),
      new THREE.Vector3(...mid),
      new THREE.Vector3(...to),
    ]).getPoints(32).map(p => [p.x, p.y, p.z] as [number, number, number])
  }, [from, to])

  return (
    <Line
      points={points}
      color="#1a3a5a"
      opacity={0.4}
      transparent
      lineWidth={1}
    />
  )
}
