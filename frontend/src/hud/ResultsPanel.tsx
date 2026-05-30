import type { RunCompleteEvent } from '../types'

interface ResultsPanelProps {
  result: RunCompleteEvent
}

export function ResultsPanel({ result }: ResultsPanelProps) {
  return (
    <div style={{ overflowY: 'auto', fontSize: '11px', lineHeight: 1.6 }}>
      <h3 style={{ color: '#00ff88', marginBottom: 8, fontSize: 13 }}>{result.company_name}</h3>

      {/* Key ratios */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ color: '#88aacc', fontWeight: 700, marginBottom: 4, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Key Ratios</div>
        {result.ratios.slice(0, 10).map(r => (
          <div key={r.finding_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <span style={{ color: '#aabbcc' }}>{r.name} ({r.period})</span>
            <span style={{ color: '#00ccff', fontFamily: 'monospace' }}>{r.value.toFixed(2)} {r.unit}</span>
          </div>
        ))}
      </div>

      {/* Flags */}
      {result.flags.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ color: '#88aacc', fontWeight: 700, marginBottom: 4, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Flags</div>
          {result.flags.map((f, i) => (
            <div key={i} style={{ color: f.severity === 'critical' ? '#ff6666' : '#ffaa00', padding: '2px 0', fontSize: 10 }}>
              [{f.severity.toUpperCase()}] {f.message.slice(0, 100)}
            </div>
          ))}
        </div>
      )}

      {/* Projections */}
      {result.projections.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ color: '#88aacc', fontWeight: 700, marginBottom: 4, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Projections</div>
          {result.projections.map((p, i) => (
            <div key={i} style={{ marginBottom: 8, background: 'rgba(0,20,40,0.5)', borderRadius: 4, padding: '6px 8px' }}>
              <div style={{ color: '#aaccee', marginBottom: 4, fontSize: 10 }}>{p.description}</div>
              {p.scenarios.map(s => (
                <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between', color: '#667788', fontSize: 10, padding: '1px 0' }}>
                  <span style={{ textTransform: 'capitalize', color: s.label === 'base' ? '#aaccee' : '#667788' }}>{s.label}</span>
                  <span style={{ fontFamily: 'monospace', color: '#00ccff' }}>
                    {s.target_value.toFixed(1)} {p.unit}
                    {s.impact_eur != null ? ` | €${s.impact_eur.toLocaleString()}` : ''}
                  </span>
                </div>
              ))}
              <div style={{ color: '#445566', fontSize: 9, marginTop: 4, fontStyle: 'italic' }}>{p.disclaimer}</div>
            </div>
          ))}
        </div>
      )}

      {/* Narrative */}
      <div>
        <div style={{ color: '#88aacc', fontWeight: 700, marginBottom: 4, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Narrative</div>
        <div style={{ color: '#99aabb', fontSize: 10, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
          {result.narrative}
        </div>
      </div>
    </div>
  )
}
