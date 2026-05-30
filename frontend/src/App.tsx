import { Suspense } from 'react'
import { PipelineScene } from './scene/PipelineScene'
import { HUD } from './hud/HUD'
import { usePipelineWS } from './hooks/usePipelineWS'

export default function App() {
  const { state, startRun } = usePipelineWS()

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', background: '#050a14' }}>
      {/* 3D Scene */}
      <Suspense fallback={null}>
        <PipelineScene pipelineState={state} />
      </Suspense>

      {/* HUD Overlay */}
      <HUD state={state} onStartRun={startRun} />
    </div>
  )
}
