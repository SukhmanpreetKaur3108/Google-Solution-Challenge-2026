import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Loader2, Send, ShieldCheck, AlertTriangle, XCircle } from 'lucide-react'
import ScoreGauge from '../components/ScoreGauge'

const SAMPLE_APPLICANTS = [
  {
    name: 'James Smith (Majority)',
    payload: {
      applicant: { name: 'James Smith', age: 32, gender: 'male', ethnicity: 'white',
        education: 'master', years_experience: 7, skills: ['python','sql','machine_learning','leadership'], current_employer: 'Google' },
      job_description: 'Senior Data Scientist — 5+ yrs exp, Python, ML required',
      model_id: 'default',
    },
  },
  {
    name: 'Lakisha Jones (Same Quals, Minority)',
    payload: {
      applicant: { name: 'Lakisha Jones', age: 32, gender: 'female', ethnicity: 'black',
        education: 'master', years_experience: 7, skills: ['python','sql','machine_learning','leadership'], current_employer: 'Google' },
      job_description: 'Senior Data Scientist — 5+ yrs exp, Python, ML required',
      model_id: 'default',
    },
  },
]

const statusIcon: Record<string, JSX.Element> = {
  FAIR:         <ShieldCheck className="text-green-400 w-5 h-5" />,
  REVIEW_NEEDED:<AlertTriangle className="text-yellow-400 w-5 h-5" />,
  BIASED:       <XCircle className="text-red-400 w-5 h-5" />,
}

export default function Demo() {
  const navigate = useNavigate()
  const [json, setJson] = useState(JSON.stringify(SAMPLE_APPLICANTS[0].payload, null, 2))
  const [result, setResult] = useState<any>(null)

  const mutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await axios.post('/api/score', payload, {
        headers: { 'X-API-Key': import.meta.env.VITE_API_KEY || 'demo' },
      })
      return res.data
    },
    onSuccess: (data) => setResult(data),
  })

  const handleSubmit = () => {
    try {
      mutation.mutate(JSON.parse(json))
    } catch {
      alert('Invalid JSON')
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Live Demo — Hiring AI Scorer</h1>
      <p className="text-gray-400 mb-8">Submit a resume → get a Fairness Certificate in real-time.</p>

      {/* Preset buttons */}
      <div className="flex gap-3 mb-4 flex-wrap">
        {SAMPLE_APPLICANTS.map(s => (
          <button key={s.name} className="btn-secondary text-sm"
            onClick={() => setJson(JSON.stringify(s.payload, null, 2))}>
            Load: {s.name}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Input */}
        <div className="card">
          <h2 className="font-semibold text-gray-300 mb-3">Request Payload (JSON)</h2>
          <textarea
            className="w-full h-80 bg-gray-950 text-green-300 font-mono text-xs p-4 rounded-xl border border-gray-700 resize-none focus:outline-none focus:border-brand-500"
            value={json}
            onChange={e => setJson(e.target.value)}
          />
          <button
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
          >
            {mutation.isPending ? <Loader2 className="animate-spin w-4 h-4" /> : <Send className="w-4 h-4" />}
            {mutation.isPending ? 'Running 5 fairness engines…' : 'Score & Generate Certificate'}
          </button>
          {mutation.isError && (
            <p className="text-red-400 text-sm mt-3">
              Error: {(mutation.error as any)?.message || 'Request failed'}
            </p>
          )}
        </div>

        {/* Result */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Decision */}
              <div className="card">
                <div className="flex items-center gap-3 mb-4">
                  {statusIcon[result.certificate_status] || statusIcon.REVIEW_NEEDED}
                  <div>
                    <div className="font-bold text-lg">{result.should_hire ? '✅ Hire' : '❌ Reject'}</div>
                    <div className="text-gray-400 text-sm">Score: {(result.candidate_score * 100).toFixed(1)}%</div>
                  </div>
                  <span className={`ml-auto badge-${result.certificate_status === 'FAIR' ? 'fair' : result.certificate_status === 'BIASED' ? 'biased' : 'review'}`}>
                    {result.certificate_status}
                  </span>
                </div>

                {/* Score gauges */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
                  <ScoreGauge score={result.fairness.statistical_score} label="Statistical" size="sm" />
                  <ScoreGauge score={result.fairness.causal_counterfactual_score} label="Causal" size="sm" />
                  <ScoreGauge score={1 - result.fairness.adversarial_flip_rate} label="Adversarial" size="sm" />
                  <ScoreGauge score={result.fairness.regulatory_compliance_percent / 100} label="Regulatory" size="sm" />
                </div>

                {result.fairness.intersectional_worst_subgroup !== 'N/A' && (
                  <div className="mt-4 text-xs text-yellow-400 bg-yellow-900/20 rounded-lg p-3">
                    ⚠️ Worst subgroup: <strong>{result.fairness.intersectional_worst_subgroup}</strong>
                  </div>
                )}
                {result.fairness.regulatory_failures.length > 0 && (
                  <div className="mt-2 text-xs text-red-400 bg-red-900/20 rounded-lg p-3">
                    ❌ Regulatory failures: {result.fairness.regulatory_failures.join(', ')}
                  </div>
                )}
              </div>

              {/* Certificate */}
              <div className="card">
                <div className="flex justify-between items-start mb-3">
                  <span className="text-gray-400 text-sm font-mono">Certificate ID</span>
                  <button className="btn-secondary text-xs" onClick={() => navigate(`/cert/${result.certificate_id}`)}>
                    View Full Certificate →
                  </button>
                </div>
                <div className="font-mono text-xs text-brand-400 break-all">{result.certificate_id}</div>
                <div className="mt-3 text-xs text-gray-500">
                  <a href={result.verification_url} target="_blank" rel="noreferrer"
                    className="text-brand-400 hover:underline">{result.verification_url}</a>
                </div>
              </div>
            </>
          ) : (
            <div className="card flex items-center justify-center h-48 text-gray-600 text-center">
              <div>
                <ShieldCheck className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Submit a request to generate<br />your Fairness Certificate</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
