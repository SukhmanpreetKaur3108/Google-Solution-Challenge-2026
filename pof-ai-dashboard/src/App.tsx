import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ── Types ─────────────────────────────────────────────────────────────────────
interface FairnessScore {
  statistical_score: number;
  intersectional_worst_subgroup: string;
  causal_counterfactual_score: number;
  adversarial_flip_rate: number;
  regulatory_compliance_percent: number;
  regulatory_failures: string[];
}
interface ApiResponse {
  decision_id: string;
  candidate_score: number;
  should_hire: boolean;
  certificate_id: string;
  certificate_status: "FAIR" | "REVIEW_NEEDED" | "BIASED";
  fairness: FairnessScore;
  verification_url: string;
  certificate_json: Record<string, unknown>;
}

const HISTORY_KEY = "pof_ai_history";

function loadHistory(): ApiResponse[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); }
  catch { return []; }
}
function saveHistory(h: ApiResponse[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, 20)));
}

// ── Shared UI ─────────────────────────────────────────────────────────────────
function statusColor(s: string) {
  if (s === "FAIR") return "text-green-400";
  if (s === "REVIEW_NEEDED") return "text-yellow-400";
  return "text-red-400";
}
function statusBg(s: string) {
  if (s === "FAIR") return "bg-green-900/30 border-green-700";
  if (s === "REVIEW_NEEDED") return "bg-yellow-900/30 border-yellow-700";
  return "bg-red-900/30 border-red-700";
}
function statusBadge(s: string) {
  const base = "px-3 py-1 rounded-full text-xs font-bold border ";
  if (s === "FAIR") return base + "bg-green-900/50 text-green-400 border-green-600";
  if (s === "REVIEW_NEEDED") return base + "bg-yellow-900/50 text-yellow-400 border-yellow-600";
  return base + "bg-red-900/50 text-red-400 border-red-600";
}

function ScoreBar({ label, value, max = 1, invert = false }: { label: string; value: number; max?: number; invert?: boolean }) {
  const display = invert ? 1 - value : value;
  const pct = Math.round((display / max) * 100);
  const color = pct >= 70 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-300">{label}</span>
        <span className="font-mono text-white">{display.toFixed(3)}</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2.5">
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8 }}
          className={`h-2.5 rounded-full ${color}`} />
      </div>
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between items-start gap-4 py-1">
      <span className="text-gray-400 text-sm shrink-0">{label}</span>
      <span className={`text-sm text-right break-all ${mono ? "font-mono text-green-400" : "text-white"}`}>{value}</span>
    </div>
  );
}

// ── Landing ───────────────────────────────────────────────────────────────────
function Landing({ setPage }: { setPage: (p: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] text-center px-4">
      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.6 }}>
        <div className="inline-block mb-4 px-4 py-1 rounded-full bg-blue-900/40 border border-blue-700 text-blue-400 text-xs tracking-widest uppercase">
          Google Solution Challenge 2026
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold mb-4 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
          Proof of Fairness AI
        </h1>
        <p className="text-gray-300 max-w-2xl text-lg mb-2">
          Every AI hiring decision comes with a <span className="text-white font-semibold">cryptographically signed Fairness Certificate</span> —
          powered by 5 bias-detection engines running in parallel.
        </p>
        <p className="text-gray-500 text-sm mb-8">
          Statistical · Intersectional · Causal · Adversarial · Regulatory
        </p>
        <div className="flex gap-4 justify-center flex-wrap mb-14">
          <motion.button whileHover={{ scale: 1.07 }} whileTap={{ scale: 0.95 }}
            onClick={() => setPage("demo")}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-semibold shadow-lg shadow-blue-900/30 transition-colors">
            Try Live Demo →
          </motion.button>
          <motion.button whileHover={{ scale: 1.07 }} whileTap={{ scale: 0.95 }}
            onClick={() => setPage("history")}
            className="px-8 py-3 border border-gray-600 hover:border-gray-400 rounded-xl font-semibold text-gray-300 transition-colors">
            View History
          </motion.button>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 max-w-5xl w-full">
        {[
          { name: "Statistical", icon: "📊", desc: "Demographic parity & equalized odds via Fairlearn" },
          { name: "Intersectional", icon: "🔀", desc: "Gender × race subgroup — catches Gender Shades bias" },
          { name: "Causal", icon: "🔗", desc: "Counterfactual: would the decision change if only race changed?" },
          { name: "Adversarial", icon: "🤖", desc: "Gemini AI generates near-twin applicants to probe flip rate" },
          { name: "Regulatory", icon: "⚖️", desc: "EU AI Act & EEOC compliance checklist" },
        ].map((e, i) => (
          <motion.div key={e.name} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * i }}
            className="bg-gray-800/60 border border-gray-700 rounded-xl p-4 text-left hover:border-blue-700 transition-colors">
            <div className="text-2xl mb-2">{e.icon}</div>
            <p className="text-blue-400 font-semibold text-sm">{e.name}</p>
            <p className="text-gray-400 text-xs mt-1">{e.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ── Demo ──────────────────────────────────────────────────────────────────────
function Demo({ onResult }: { onResult: (r: ApiResponse) => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [form, setForm] = useState({
    name: "Alex Johnson",
    age: "30",
    gender: "female",
    ethnicity: "black",
    education: "Bachelor's",
    years_experience: "5",
    skills: "Python, Machine Learning, SQL",
    current_employer: "TechCorp",
    job_description: "Senior Data Scientist role requiring ML expertise",
  });

  const set = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          applicant: {
            name: form.name,
            age: parseInt(form.age),
            gender: form.gender,
            ethnicity: form.ethnicity,
            education: form.education,
            years_experience: parseInt(form.years_experience),
            skills: form.skills.split(",").map((s) => s.trim()).filter(Boolean),
            current_employer: form.current_employer,
          },
          job_description: form.job_description,
          model_id: "default",
        }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || `Server error ${res.status}`);
      }
      const data: ApiResponse = await res.json();
      setResponse(data);
      onResult(data);
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message.includes("fetch")) {
        setError("Cannot reach backend. Make sure the backend server is running: open a second terminal → cd pof-ai-backend → .venv\\Scripts\\uvicorn.exe app.main:app --reload --port 8000");
      } else {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    } finally {
      setLoading(false);
    }
  };

  const inp = "w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500";
  const lbl = "block text-gray-400 text-xs mb-1 font-medium";

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold mb-2">Live Hiring Bias Detector</h2>
      <p className="text-gray-400 text-sm mb-6">Fill in applicant details and run all 5 fairness engines in real time.</p>

      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 mb-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">Applicant Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div><label className={lbl}>Full Name</label><input className={inp} name="name" value={form.name} onChange={set} /></div>
          <div><label className={lbl}>Age</label><input className={inp} name="age" type="number" min="18" max="80" value={form.age} onChange={set} /></div>
          <div><label className={lbl}>Gender</label>
            <select className={inp} name="gender" value={form.gender} onChange={set}>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="non-binary">Non-binary</option>
            </select>
          </div>
          <div><label className={lbl}>Ethnicity</label>
            <select className={inp} name="ethnicity" value={form.ethnicity} onChange={set}>
              <option value="black">Black</option>
              <option value="white">White</option>
              <option value="asian">Asian</option>
              <option value="hispanic">Hispanic</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div><label className={lbl}>Education</label>
            <select className={inp} name="education" value={form.education} onChange={set}>
              <option>High School</option>
              <option>Bachelor's</option>
              <option>Master's</option>
              <option>PhD</option>
            </select>
          </div>
          <div><label className={lbl}>Years of Experience</label><input className={inp} name="years_experience" type="number" min="0" max="50" value={form.years_experience} onChange={set} /></div>
          <div><label className={lbl}>Current Employer</label><input className={inp} name="current_employer" value={form.current_employer} onChange={set} /></div>
          <div><label className={lbl}>Skills (comma-separated)</label><input className={inp} name="skills" value={form.skills} onChange={set} /></div>
          <div className="md:col-span-2"><label className={lbl}>Job Description</label>
            <textarea className={inp + " h-20 resize-none"} name="job_description" value={form.job_description} onChange={set} />
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-900/40 border border-red-700 rounded-xl text-red-300 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
        onClick={handleSubmit} disabled={loading}
        className="w-full md:w-auto px-10 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-xl font-semibold text-base transition-colors shadow-lg shadow-blue-900/20">
        {loading ? (
          <span className="flex items-center gap-2 justify-center">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            Running 5 engines…
          </span>
        ) : "Run Fairness Analysis"}
      </motion.button>

      <AnimatePresence>
        {response && (
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="mt-8 space-y-4">
            {/* Decision */}
            <div className={`p-6 rounded-2xl border ${statusBg(response.certificate_status)}`}>
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <p className="text-xs text-gray-400 mb-1 uppercase tracking-wider">AI Decision</p>
                  <p className="text-3xl font-bold">{response.should_hire ? "✓ Recommended" : "✗ Not Recommended"}</p>
                  <p className="text-gray-400 mt-1">Candidate score: <span className="text-white font-mono">{(response.candidate_score * 100).toFixed(1)}%</span></p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400 mb-2 uppercase tracking-wider">Certificate</p>
                  <span className={statusBadge(response.certificate_status)}>
                    {response.certificate_status.replace("_", " ")}
                  </span>
                </div>
              </div>
            </div>

            {/* Engine results */}
            <div className="p-6 bg-gray-900 rounded-2xl border border-gray-700">
              <h3 className="font-bold mb-5 text-gray-100 flex items-center gap-2">
                <span>⚙️</span> Fairness Engine Results
              </h3>
              <ScoreBar label="Statistical Fairness" value={response.fairness.statistical_score} />
              <ScoreBar label="Causal Counterfactual Fairness" value={response.fairness.causal_counterfactual_score} />
              <ScoreBar label="Adversarial Robustness (1 − flip rate)" value={response.fairness.adversarial_flip_rate} invert />
              <ScoreBar label="Regulatory Compliance" value={response.fairness.regulatory_compliance_percent} max={100} />

              <div className="mt-4 p-3 bg-gray-800 rounded-xl">
                <span className="text-xs text-gray-400 uppercase tracking-wider">Intersectional worst subgroup: </span>
                <span className="text-yellow-400 font-mono text-sm ml-1">{response.fairness.intersectional_worst_subgroup}</span>
              </div>

              {response.fairness.regulatory_failures.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs text-gray-400 mb-2 uppercase tracking-wider">Regulatory failures:</p>
                  <div className="flex flex-wrap gap-2">
                    {response.fairness.regulatory_failures.map((f) => (
                      <span key={f} className="px-2 py-1 bg-red-900/50 border border-red-700 rounded-lg text-xs text-red-300">{f}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* IDs */}
            <div className="p-4 bg-gray-900/60 rounded-xl border border-gray-800 font-mono text-xs text-gray-500 space-y-1">
              <p>decision_id: {response.decision_id}</p>
              <p>certificate_id: {response.certificate_id}</p>
            </div>

            <p className="text-xs text-gray-500 text-center">
              Certificate saved to history. Switch to the <strong className="text-gray-400">Certificate</strong> tab to view the signed document.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Certificate ───────────────────────────────────────────────────────────────
function Certificate({ data }: { data: ApiResponse | null }) {
  if (!data) {
    return (
      <div className="p-10 text-center">
        <div className="text-6xl mb-4">📜</div>
        <p className="text-xl text-gray-300 mb-2">No certificate yet</p>
        <p className="text-gray-500 text-sm">Run the Demo first, then come back here to see the signed Fairness Certificate.</p>
      </div>
    );
  }

  const cert = data.certificate_json;
  const sig = cert["proof"] as Record<string, unknown> | undefined;
  const sigVal = String(sig?.["signatureValue"] ?? "");

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h2 className="text-3xl font-bold mb-6">Fairness Certificate</h2>
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="border border-gray-600 rounded-2xl shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="bg-gradient-to-r from-blue-900 via-purple-900 to-indigo-900 p-8 text-center">
          <div className="text-4xl mb-3">🏅</div>
          <p className="text-xs text-blue-300 mb-1 tracking-widest uppercase">Proof of Fairness AI</p>
          <h2 className="text-2xl font-bold">Fairness Certificate</h2>
          <div className="mt-3">
            <span className={statusBadge(data.certificate_status)}>
              {data.certificate_status.replace("_", " ")} ✓
            </span>
          </div>
        </div>

        {/* Fields */}
        <div className="bg-gray-900 p-6 divide-y divide-gray-800">
          <Row label="Certificate ID" value={data.certificate_id} mono />
          <Row label="Decision ID" value={data.decision_id} mono />
          <Row label="Candidate Score" value={`${(data.candidate_score * 100).toFixed(1)}%`} />
          <Row label="Decision" value={data.should_hire ? "✓ Hire" : "✗ Do Not Hire"} />
          <div className="py-2" />
          <Row label="Statistical Fairness" value={data.fairness.statistical_score.toFixed(4)} />
          <Row label="Causal Score" value={data.fairness.causal_counterfactual_score.toFixed(4)} />
          <Row label="Adversarial Flip Rate" value={data.fairness.adversarial_flip_rate.toFixed(4)} />
          <Row label="Regulatory Compliance" value={`${data.fairness.regulatory_compliance_percent.toFixed(1)}%`} />
          <Row label="Worst Subgroup" value={data.fairness.intersectional_worst_subgroup} />
          {sig && (
            <>
              <div className="py-2" />
              <Row label="Signature Type" value={String(sig["type"] ?? "—")} mono />
              <Row label="Signature" value={sigVal ? `${sigVal.slice(0, 48)}…` : "—"} mono />
            </>
          )}
        </div>

        {/* Raw JSON */}
        <details className="bg-gray-950 border-t border-gray-800">
          <summary className="px-6 py-3 cursor-pointer text-xs text-gray-500 hover:text-gray-300 select-none">
            🔍 View raw certificate JSON (JSON-LD)
          </summary>
          <pre className="px-6 pb-6 text-xs text-green-400 overflow-auto max-h-96 font-mono">
            {JSON.stringify(cert, null, 2)}
          </pre>
        </details>
      </motion.div>
    </div>
  );
}

// ── History ───────────────────────────────────────────────────────────────────
function History({ onSelect, setPage }: { onSelect: (r: ApiResponse) => void; setPage: (p: string) => void }) {
  const [history, setHistory] = useState<ApiResponse[]>(loadHistory);

  const clear = () => { localStorage.removeItem(HISTORY_KEY); setHistory([]); };

  if (history.length === 0) {
    return (
      <div className="p-10 text-center text-gray-400">
        <div className="text-5xl mb-4">🗂️</div>
        <p className="text-lg mb-2">No history yet</p>
        <p className="text-sm">Analyses you run will be saved here (up to 20 entries).</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold">Analysis History</h2>
        <button onClick={clear} className="text-xs text-red-400 hover:text-red-300 border border-red-800 px-3 py-1.5 rounded-lg">
          Clear all
        </button>
      </div>
      <div className="space-y-3">
        {history.map((r, i) => (
          <motion.div key={r.decision_id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
            className="flex items-center justify-between p-4 bg-gray-900 border border-gray-700 rounded-xl hover:border-gray-500 transition-colors">
            <div className="flex items-center gap-4">
              <span className={statusBadge(r.certificate_status)}>{r.certificate_status.replace("_", " ")}</span>
              <div>
                <p className="text-sm text-white font-mono">{r.certificate_id.slice(0, 16)}…</p>
                <p className="text-xs text-gray-500">Score: {(r.candidate_score * 100).toFixed(1)}% · {r.should_hire ? "Hire" : "No hire"}</p>
              </div>
            </div>
            <button
              onClick={() => { onSelect(r); setPage("cert"); }}
              className="text-xs text-blue-400 hover:text-blue-300 border border-blue-800 px-3 py-1.5 rounded-lg">
              View cert →
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ── App Shell ─────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState("home");
  const [lastResult, setLastResult] = useState<ApiResponse | null>(null);

  const handleResult = (r: ApiResponse) => {
    const h = loadHistory();
    h.unshift(r);
    saveHistory(h);
    setLastResult(r);
  };

  const nav = [
    ["home", "Home"],
    ["demo", "Demo"],
    ["cert", "Certificate"],
    ["history", "History"],
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-800 text-white">
      {/* Navbar */}
      <nav className="flex justify-between items-center px-6 py-4 border-b border-gray-800 sticky top-0 bg-gray-950/80 backdrop-blur-md z-50">
        <button onClick={() => setPage("home")}
          className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent hover:opacity-80 transition-opacity">
          PoF-AI
        </button>
        <div className="flex gap-1">
          {nav.map(([id, label]) => (
            <button key={id} onClick={() => setPage(id)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                page === id
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-900/30"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}>
              {label}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <AnimatePresence mode="wait">
        <motion.div key={page}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}>
          {page === "home"    && <Landing setPage={setPage} />}
          {page === "demo"    && <Demo onResult={handleResult} />}
          {page === "cert"    && <Certificate data={lastResult} />}
          {page === "history" && <History onSelect={setLastResult} setPage={setPage} />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
