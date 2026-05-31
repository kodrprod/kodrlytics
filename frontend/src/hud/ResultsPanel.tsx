import type { RunCompleteEvent } from '../types'

const ACCENT = '#FF6600'
const BLACK  = '#111111'
const GREY   = '#888888'

interface ResultsPanelProps {
  result: RunCompleteEvent
}

export function ResultsPanel({ result }: ResultsPanelProps) {
  return (
    <div style={{ overflowY: 'auto', fontSize: 10, fontFamily: '"Courier New", monospace', lineHeight: 1.6, color: BLACK }}>

      <div style={{ fontSize: 13, fontWeight: 700, color: BLACK, marginBottom: 8, borderBottom: `2px solid ${ACCENT}`, paddingBottom: 6 }}>
        {result.company_name}
      </div>

      {/* Key ratios */}
      <div style={{ marginBottom: 10 }}>
        <div style={sectionLabel}>KEY RATIOS</div>
        {result.ratios.slice(0, 10).map(r => (
          <div key={r.finding_id} style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '2px 0', borderBottom: '1px solid #F0F0F0',
          }}>
            <span style={{ color: GREY, fontSize: 9 }}>{r.name} ({r.period})</span>
            <span style={{ color: ACCENT, fontWeight: 700, fontSize: 9 }}>
              {r.value.toFixed(2)} {r.unit}
            </span>
          </div>
        ))}
      </div>

      {/* Flags */}
      {result.flags.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <div style={sectionLabel}>FLAGS</div>
          {result.flags.map((f, i) => (
            <div key={i} style={{
              fontSize: 8.5, padding: '2px 0',
              color: f.severity === 'critical' ? '#CC0000' : '#FF8800',
              borderBottom: '1px solid #F0F0F0',
            }}>
              [{f.severity.toUpperCase()}] {f.message.slice(0, 80)}
            </div>
          ))}
        </div>
      )}

      {/* Projections */}
      {result.projections.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <div style={sectionLabel}>PROJECTIONS</div>
          {result.projections.map((p, i) => (
            <div key={i} style={{ marginBottom: 7, paddingBottom: 7, borderBottom: '1px solid #E0E0E0' }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: BLACK, marginBottom: 2 }}>{p.description}</div>
              {p.scenarios.map(s => (
                <div key={s.label} style={{
                  display: 'flex', justifyContent: 'space-between',
                  fontSize: 8.5, color: GREY, padding: '1px 0',
                }}>
                  <span style={{ textTransform: 'capitalize', color: s.label === 'base' ? BLACK : GREY }}>{s.label}</span>
                  <span style={{ color: ACCENT }}>
                    {s.target_value.toFixed(1)} {p.unit}
                    {s.impact_eur != null ? ` | EUR ${s.impact_eur.toLocaleString()}` : ''}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Narrative */}
      <div>
        <div style={sectionLabel}>NARRATIVE</div>
        <div style={{ fontSize: 8.5, color: GREY, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
          {result.narrative}
        </div>
      </div>

    </div>
  )
}

const sectionLabel: React.CSSProperties = {
  fontSize: 8, fontWeight: 700, color: GREY,
  letterSpacing: '0.2em', marginBottom: 4,
}
