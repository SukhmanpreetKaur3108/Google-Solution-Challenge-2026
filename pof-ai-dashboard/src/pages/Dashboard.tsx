import { useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import { AlertTriangle } from 'lucide-react'
import ScoreGauge from '../components/ScoreGauge'

// Mock weekly data — replace with TanStack Query fetching /api/metrics in production
const WEEKLY_DATA = [
  { week: 'W1', statistical: 0.91, causal: 0.88, adversarial: 0.82, regulatory: 0.92 },
  { week: 'W2', statistical: 0.89, causal: 0.85, adversarial: 0.80, regulatory: 0.92 },
  { week: 'W3', statistical: 0.87, causal: 0.84, adversarial: 0.78, regulatory: 0.83 },
  { week: 'W4', statistical: 0.85, causal: 0.82, adversarial: 0.75, regulatory: 0.83 },
  { week: 'W5', statistical: 0.82, causal: 0.80, adversarial: 0.72, regulatory: 0.75 },
  { week: 'W6', statistical: 0.78, causal: 0.77, adversarial: 0.69, regulatory: 0.67 },
]

const BASELINE = { statistical: 0.91, causal: 0.88, adversarial: 0.82, regulatory: 0.92 }
const DRIFT_THRESHOLD = 0.1
const latest = WEEKLY_DATA[WEEKLY_DATA.length - 1]
const drifted = (Object.keys(BASELINE) as Array<keyof typeof BASELINE>).filter(
  k => BASELINE[k] - latest[k] > DRIFT_THRESHOLD
)

const SUBGROUP_HEATMAP = [
  { gender: 'Male',   ethnicity: 'White',    rate: 0.62 },
  { gender: 'Male',   ethnicity: 'Black',    rate: 0.51 },
  { gender: 'Male',   ethnicity: 'Asian',    rate: 0.59 },
  { gender: 'Male',   ethnicity: 'Hispanic', rate: 0.50 },
  { gender: 'Female', ethnicity: 'White',    rate: 0.56 },
  { gender: 'Female', ethnicity: 'Black',    rate: 0.40 },
  { gender: 'Female', ethnicity: 'Asian',    rate: 0.53 },
  { gender: 'Female', ethnicity: 'Hispanic', rate: 0.39 },
]

const COLORS = {
  statistical: '#6366f1',
  causal:      '#22c55e',
  adversarial: '#f59e0b',
  regulatory:  '#3b82f6',
}

export default function Dashboard() {
  const genders    = [...new Set(SUBGROUP_HEATMAP.map(d => d.gender))]
  const ethnicities = [...new Set(SUBGROUP_HEATMAP.map(d => d.ethnicity))]

  return (
    <div className="max-w-6xl mx-auto px-6 py-12 space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Fairness Dashboard</h1>
        <p className="text-gray-400">Organisation-wide bias monitoring — weekly fairness scores and drift alerts.</p>
      </div>

      {/* Drift alert banner */}
      {drifted.length > 0 && (
        <div className="flex items-center gap-3 bg-red-900/30 border border-red-700 rounded-2xl p-4 text-red-300">
          <AlertTriangle className="w-6 h-6 flex-shrink-0" />
          <div>
            <strong>Drift Alert:</strong> The following metrics have drifted &gt;10% from baseline this week:{' '}
            <strong>{drifted.join(', ')}</strong>. Immediate review recommended.
          </div>
        </div>
      )}

      {/* Current week scores */}
      <div className="card">
        <h2 className="font-semibold mb-6">Current Week — Overall Scores</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 justify-items-center">
          <ScoreGauge score={latest.statistical}  label="Statistical"  size="lg" />
          <ScoreGauge score={latest.causal}        label="Causal CF"    size="lg" />
          <ScoreGauge score={latest.adversarial}   label="Adversarial"  size="lg" />
          <ScoreGauge score={latest.regulatory}    label="Regulatory"   size="lg" />
        </div>
      </div>

      {/* Line chart — weekly trends */}
      <div className="card">
        <h2 className="font-semibold mb-6">6-Week Fairness Trend</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={WEEKLY_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="week" stroke="#6b7280" tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <YAxis domain={[0.5, 1]} stroke="#6b7280" tick={{ fill: '#9ca3af', fontSize: 12 }} tickFormatter={v => `${Math.round(v * 100)}%`} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 12 }}
              formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
            />
            <Legend />
            <ReferenceLine y={BASELINE.statistical - DRIFT_THRESHOLD} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Drift limit', fill: '#ef4444', fontSize: 11 }} />
            {(Object.keys(COLORS) as Array<keyof typeof COLORS>).map(k => (
              <Line key={k} type="monotone" dataKey={k} stroke={COLORS[k]} strokeWidth={2.5}
                dot={{ r: 4, fill: COLORS[k] }} activeDot={{ r: 6 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Intersectional heatmap */}
      <div className="card">
        <h2 className="font-semibold mb-2">Intersectional Selection Rate Heatmap</h2>
        <p className="text-gray-500 text-sm mb-6">Hire rate by gender × ethnicity. Red = most disadvantaged subgroup.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left text-gray-500 pb-3 pr-4">Gender \ Ethnicity</th>
                {ethnicities.map(e => <th key={e} className="text-gray-400 pb-3 px-4">{e}</th>)}
              </tr>
            </thead>
            <tbody>
              {genders.map(g => (
                <tr key={g}>
                  <td className="text-gray-400 py-2 pr-4 font-medium">{g}</td>
                  {ethnicities.map(e => {
                    const cell = SUBGROUP_HEATMAP.find(d => d.gender === g && d.ethnicity === e)
                    const rate = cell?.rate ?? 0
                    const bg = rate >= 0.58 ? 'bg-green-900/40' : rate >= 0.48 ? 'bg-yellow-900/40' : 'bg-red-900/50'
                    const text = rate >= 0.58 ? 'text-green-300' : rate >= 0.48 ? 'text-yellow-300' : 'text-red-300'
                    return (
                      <td key={e} className={`py-2 px-4 rounded text-center font-semibold ${bg} ${text}`}>
                        {(rate * 100).toFixed(0)}%
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-red-400 mt-4">
          ⚠️ Worst: Female × Black (39%) and Female × Hispanic (39%) — 23pp below majority group
        </p>
      </div>
    </div>
  )
}
