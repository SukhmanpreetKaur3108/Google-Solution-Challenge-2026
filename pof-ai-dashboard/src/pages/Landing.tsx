import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldCheck, Zap, Globe, Scale, ArrowRight, CheckCircle } from 'lucide-react'

const ENGINES = [
  { icon: '📊', name: 'Statistical',    desc: 'Fairlearn metrics: demographic parity, equalized odds, disparate impact' },
  { icon: '🔀', name: 'Intersectional', desc: 'Bias across subgroup intersections — catches what gender-only checks miss' },
  { icon: '🔗', name: 'Causal',         desc: 'DoWhy counterfactual: would outcome change if only protected attribute changed?' },
  { icon: '🤖', name: 'Adversarial',    desc: 'Gemini-powered near-twin probes — same quals, different name/gender/ethnicity' },
  { icon: '⚖️', name: 'Regulatory',    desc: 'EU AI Act · GDPR Art.22 · NIST AI RMF · India DPDP Act 2023' },
]

const STATS = [
  { value: '5', label: 'Fairness Engines' },
  { value: '12+', label: 'Regulatory Clauses' },
  { value: '100%', label: 'Decisions Certified' },
  { value: '<2s', label: 'Per Certificate' },
]

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="overflow-hidden">
      {/* Hero */}
      <section className="relative min-h-[90vh] flex items-center justify-center px-6">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-brand-600/10 rounded-full blur-3xl" />
        </div>

        <div className="max-w-5xl mx-auto text-center z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}
          >
            <div className="inline-flex items-center gap-2 bg-brand-900/50 border border-brand-700 text-brand-300 text-sm font-medium px-4 py-2 rounded-full mb-8">
              <ShieldCheck className="w-4 h-4" /> Google Solution Challenge 2026
            </div>

            <h1 className="text-6xl md:text-7xl font-extrabold text-white leading-tight mb-6">
              AI Decisions That Come<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-purple-400">
                With Proof
              </span>
            </h1>

            <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-12">
              PoF-AI doesn't just detect bias — it mathematically proves every hiring decision
              is fair, signs the proof cryptographically, and creates a tamper-evident audit trail.
              Like <strong className="text-gray-200">SSL certificates for AI decisions</strong>.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button onClick={() => navigate('/demo')} className="btn-primary flex items-center gap-2 text-base">
                Try Live Demo <ArrowRight className="w-4 h-4" />
              </button>
              <button onClick={() => navigate('/explorer')} className="btn-secondary text-base">
                Browse Certificates
              </button>
            </div>
          </motion.div>

          {/* Decision → Certificate animation */}
          <motion.div
            initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.8 }}
            className="mt-20"
          >
            <DecisionFlowAnimation />
          </motion.div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 border-y border-gray-800 bg-gray-900/50">
        <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {STATS.map(s => (
            <div key={s.label}>
              <div className="text-4xl font-extrabold text-brand-400">{s.value}</div>
              <div className="text-gray-400 text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Five Engines */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">Five Layers of Fairness Proof</h2>
          <p className="text-gray-400 text-center mb-12">
            Every certificate is produced by five independent engines running in parallel.
          </p>
          <div className="grid md:grid-cols-5 gap-4">
            {ENGINES.map((e, i) => (
              <motion.div
                key={e.name}
                className="card hover:border-brand-600 transition-colors cursor-default"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                viewport={{ once: true }}
              >
                <div className="text-3xl mb-3">{e.icon}</div>
                <div className="font-semibold text-white mb-2">{e.name}</div>
                <div className="text-gray-400 text-xs leading-relaxed">{e.desc}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Vision */}
      <section className="py-24 px-6 bg-gray-900/40">
        <div className="max-w-3xl mx-auto text-center">
          <Globe className="w-12 h-12 text-brand-400 mx-auto mb-6" />
          <h2 className="text-3xl font-bold mb-6">2036 Vision</h2>
          <p className="text-gray-300 text-lg leading-relaxed mb-8">
            PoF-AI becomes the global standard for AI accountability. Governments require
            Fairness Certificates for all high-stakes AI decisions. AI without proof of fairness
            becomes illegal — the way SSL became mandatory for web transactions.
          </p>
          {['Courts require Fairness Certificates', 'Banks & hiring platforms certified by default',
            'Real-time global bias monitoring network', 'Cross-border regulatory compliance'].map(item => (
            <div key={item} className="flex items-center gap-3 text-gray-300 mb-3 justify-center">
              <CheckCircle className="text-green-500 w-5 h-5 flex-shrink-0" />
              {item}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function DecisionFlowAnimation() {
  const steps = [
    { label: 'Decision', icon: '📄', color: 'border-gray-600' },
    { label: 'Statistical', icon: '📊', color: 'border-blue-600' },
    { label: 'Adversarial', icon: '🤖', color: 'border-purple-600' },
    { label: 'Regulatory', icon: '⚖️', color: 'border-yellow-600' },
    { label: '✅ Certificate', icon: '🔏', color: 'border-green-500' },
  ]
  return (
    <div className="flex items-center justify-center gap-2 flex-wrap">
      {steps.map((s, i) => (
        <div key={s.label} className="flex items-center gap-2">
          <motion.div
            className={`border-2 ${s.color} bg-gray-900 rounded-xl px-4 py-3 text-center min-w-[90px]`}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.6 + i * 0.15, type: 'spring' }}
          >
            <div className="text-2xl">{s.icon}</div>
            <div className="text-xs text-gray-400 mt-1">{s.label}</div>
          </motion.div>
          {i < steps.length - 1 && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 0.9 + i * 0.15 }}
              className="text-gray-600 text-lg"
            >→</motion.div>
          )}
        </div>
      ))}
    </div>
  )
}
