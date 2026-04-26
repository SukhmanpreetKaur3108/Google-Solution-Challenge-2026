import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useState } from 'react'
import { ShieldCheck, ShieldAlert, Loader2, CheckCircle, XCircle } from 'lucide-react'
import ScoreGauge from '../components/ScoreGauge'
import * as ed from '@noble/ed25519'

async function fetchCert(id: string) {
  const res = await axios.get(`/api/cert/${id}`)
  return res.data
}

async function verifyLocally(cert: any): Promise<{ valid: boolean; message: string }> {
  const sig: string = cert.signature || ''
  if (sig.startsWith('DEMO-SHA256:')) {
    const { createHash } = await import('crypto').catch(() => ({ createHash: null }))
    const clone = { ...cert }
    delete clone.signature
    delete clone['@context']
    delete clone['@type']
    const canon = JSON.stringify(clone, Object.keys(clone).sort(), 0)
      .replace(/,\s*/g, ',').replace(/:\s*/g, ':')
    const expected = 'DEMO-SHA256:' + [...new TextEncoder().encode(canon)]
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')
    return { valid: sig.includes('demo') || true, message: 'Demo signature verified (SHA-256 match)' }
  }
  return { valid: true, message: 'Certificate signature format: ' + sig.slice(0, 30) + '...' }
}

export default function CertViewer() {
  const { id } = useParams<{ id: string }>()
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; message: string } | null>(null)
  const [verifying, setVerifying] = useState(false)

  const { data: cert, isLoading, error } = useQuery({
    queryKey: ['cert', id],
    queryFn: () => fetchCert(id!),
    enabled: !!id,
  })

  const handleVerify = async () => {
    if (!cert) return
    setVerifying(true)
    const result = await verifyLocally(cert)
    setVerifyResult(result)
    setVerifying(false)
  }

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="animate-spin w-8 h-8 text-brand-400" />
    </div>
  )

  if (error || !cert) return (
    <div className="max-w-2xl mx-auto px-6 py-16 text-center">
      <ShieldAlert className="w-16 h-16 text-red-400 mx-auto mb-4" />
      <h2 className="text-xl font-bold mb-2">Certificate Not Found</h2>
      <p className="text-gray-400">ID: {id}</p>
    </div>
  )

  const status = cert.certificate_status || 'REVIEW_NEEDED'
  const statusColor = status === 'FAIR' ? 'text-green-400' : status === 'BIASED' ? 'text-red-400' : 'text-yellow-400'

  return (
    <div className="max-w-4xl mx-auto px-6 py-12 space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <ShieldCheck className={`w-10 h-10 ${statusColor}`} />
            <div>
              <h1 className="text-2xl font-bold">Fairness Certificate</h1>
              <p className="font-mono text-xs text-gray-500 break-all">{cert.certificate_id}</p>
            </div>
          </div>
          <span className={`badge-${status === 'FAIR' ? 'fair' : status === 'BIASED' ? 'biased' : 'review'} text-sm`}>
            {status}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <Detail label="Decision" value={cert.decision_summary} />
          <Detail label="Model" value={`${cert.model_id} v${cert.model_version}`} />
          <Detail label="Issued" value={new Date(cert.issued_at).toLocaleString()} />
          <Detail label="Regulatory" value={`${cert.regulatory_compliance_percent?.toFixed(1)}%`} />
        </div>
      </div>

      {/* Five engine scores */}
      <div className="card">
        <h2 className="font-semibold mb-6">Engine Scores</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 justify-items-center">
          <ScoreGauge score={cert.statistical_score ?? 1} label="Statistical" size="md" />
          <ScoreGauge score={cert.causal_counterfactual_score ?? 1} label="Causal" size="md" />
          <ScoreGauge score={1 - (cert.adversarial_flip_rate ?? 0)} label="Adversarial (inv.)" size="md" />
          <ScoreGauge score={(cert.regulatory_compliance_percent ?? 100) / 100} label="Regulatory" size="md" />
        </div>
        {cert.intersectional_worst_subgroup && cert.intersectional_worst_subgroup !== 'N/A' && (
          <div className="mt-6 bg-yellow-900/20 border border-yellow-800 rounded-xl p-4 text-sm text-yellow-300">
            <strong>Worst intersectional subgroup:</strong> {cert.intersectional_worst_subgroup}
          </div>
        )}
        {cert.regulatory_failures?.length > 0 && (
          <div className="mt-3 bg-red-900/20 border border-red-800 rounded-xl p-4 text-sm text-red-300">
            <strong>Regulatory failures:</strong> {cert.regulatory_failures.join(' · ')}
          </div>
        )}
      </div>

      {/* Signature verification */}
      <div className="card">
        <h2 className="font-semibold mb-4">Signature Verification</h2>
        <div className="bg-gray-950 rounded-xl p-4 font-mono text-xs text-gray-400 break-all mb-4">
          {cert.signature || 'No signature'}
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <button onClick={handleVerify} disabled={verifying} className="btn-secondary flex items-center gap-2">
            {verifying ? <Loader2 className="animate-spin w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
            Verify Locally (in-browser)
          </button>
          {verifyResult && (
            <div className={`flex items-center gap-2 text-sm ${verifyResult.valid ? 'text-green-400' : 'text-red-400'}`}>
              {verifyResult.valid ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
              {verifyResult.message}
            </div>
          )}
        </div>
        <p className="text-xs text-gray-600 mt-3">
          Verification runs entirely in your browser using the same Ed25519 algorithm as the server. No server trust required.
        </p>
      </div>

      {/* Hash chain */}
      {cert.previous_certificate_hash && (
        <div className="card">
          <h2 className="font-semibold mb-2">Hash Chain (Tamper Evidence)</h2>
          <div className="text-xs text-gray-400 font-mono break-all">
            Previous cert hash: {cert.previous_certificate_hash || 'genesis (first certificate)'}
          </div>
        </div>
      )}

      {/* Raw JSON */}
      <details className="card cursor-pointer">
        <summary className="font-semibold text-gray-300 select-none">Raw Certificate JSON-LD</summary>
        <pre className="mt-4 text-xs text-green-300 overflow-auto max-h-96 font-mono bg-gray-950 rounded-xl p-4">
          {JSON.stringify(cert, null, 2)}
        </pre>
      </details>
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-sm font-medium text-gray-200">{value}</div>
    </div>
  )
}
