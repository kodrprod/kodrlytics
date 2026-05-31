import { useState } from 'react'
import { OfficeView } from './scene/OfficeView'
import { HUD } from './hud/HUD'
import { usePipelineWS } from './hooks/usePipelineWS'

export default function App() {
  const { state, startRun } = usePipelineWS()
  const [activeFloor, setActiveFloor] = useState(0)

  return (
    <div style={{
      width: '100vw', height: '100vh',
      display: 'flex', flexDirection: 'row',
      background: '#080808',
      fontFamily: '"Courier New", Courier, monospace',
      overflow: 'hidden',
    }}>
      <HUD state={state} onStartRun={startRun} />
      <OfficeView state={state} activeFloor={activeFloor} onFloorChange={setActiveFloor} />
    </div>
  )
}
