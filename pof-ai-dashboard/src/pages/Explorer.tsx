import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { ShieldCheck, ShieldAlert, AlertTriangle, Loader2, ExternalLink } from 'lucide-react'

async function fetchCerts() {
  // In production, this calls a /certs list endpoint.
  // For demo, return mock data.
  try {
    const res = await axios.get('/api/certs?limit=20')
    return res.data
  } catch {
    return MOCK_CERTS
  }
}

const MOCK_CERTS = [
  { certificate_id: 'demo-001', decision_summary: 'Hire: James Smith', certificate_status: 'FAIR', issued_at: new Date().toISOString(), statistical_score: 0.93, regulatory_compliance_percent: 100 },
  { certificate_id: 'demo-002', decision_summary: 'Reject: Lakisha Jones', certificate_status: 'BIASED', issued_at: new Date().toISOString(), statistical_score: 0.61, regulatory_compliance_percent: 58.3 },
  { certificate_id: 'demo-003', decision_summary: 'Hire: Carlos Garcia', certificate_status: 'REVIEW_NEEDED', issued_at: new Date().toISOString(), statistical_score: 0.74, regulatory_compliance_percent: 75 },
]

const statusIcon = {
  FAIR:          <ShieldCheck className="text-green-400 w-4 h-4" />,
  REVIEW_NEEDED: <AlertTriangle className="text-yellow-400 w-4 h-4" />,
  BIASED:        <ShieldAlert className="text-red-400 w-4 h-4" />,
}

export default function Explorer() {
  const navigate = useNavigate()
  const { data: certs = [], isLoading } = useQuery({
    queryKey: ['certs'],
    queryFn: fetchCerts,
  })

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Certificate Explorer</h1>
      <p className="text-gray-400 mb-8">Browse the tamper-evident audit log of all Fairness Certificates.</p>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="animate-spin w-8 h-8 text-brand-400" />
        </div>
      ) : (
        <div className="space-y-3">
          {certs.map((c: any) => (
            <div
              key={c.certificate_id}
              onClick={() => navigate(`/cert/${c.certificate_id}`)}
              className="card flex items-center gap-4 cursor-pointer hover:border-brand-600 transition-colors group"
            >
              {statusIcon[c.certificate_status as keyof typeof statusIcon] || statusIcon.REVIEW_NEEDED}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-white truncate">{c.decision_summary}</div>
                <div className="text-xs text-gray-500 font-mono truncate">{c.certificate_id}</div>
              </div>
              <div className="text-xs text-gray-400 whitespace-nowrap hidden sm:block">
                {new Date(c.issued_at).toLocaleDateString()}
              </div>
              <div className="text-right hidden md:block">
                <div className="text-xs text-gray-400">Statistical</div>
                <div className={`text-sm font-semibold ${
                  (c.statistical_score ?? 1) >= 0.8 ? 'text-green-400' :
                  (c.statistical_score ?? 1) >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                }`}>{((c.statistical_score ?? 1) * 100).toFixed(0)}%</div>
              </div>
              <div className="text-right hidden md:block">
                <div className="text-xs text-gray-400">Compliance</div>
                <div className={`text-sm font-semibold ${
                  (c.regulatory_compliance_percent ?? 100) >= 80 ? 'text-green-400' :
                  (c.regulatory_compliance_percent ?? 100) >= 60 ? 'text-yellow-400' : 'text-red-400'
                }`}>{(c.regulatory_compliance_percent ?? 100).toFixed(0)}%</div>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-600 group-hover:text-brand-400 transition-colors flex-shrink-0" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
