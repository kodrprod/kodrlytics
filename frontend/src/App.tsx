import { useState } from 'react'
import { FloorView } from './scene/FloorView'
import { HUD } from './hud/HUD'
import { usePipelineWS } from './hooks/usePipelineWS'

export default function App() {
  const { state, startRun } = usePipelineWS()
  const [activeFloor, setActiveFloor] = useState(0)

  return (
    <div style={{
      width: '100vw', height: '100vh',
      display: 'flex', flexDirection: 'row',
      background: '#FFFFFF',
      fontFamily: '"Courier New", Courier, monospace',
      overflow: 'hidden',
    }}>
      <HUD state={state} onStartRun={startRun} />
      <FloorView state={state} activeFloor={activeFloor} onFloorChange={setActiveFloor} />
    </div>
  )
}
