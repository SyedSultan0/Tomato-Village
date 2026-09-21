import { useState, useEffect } from 'react'
import { createHealthReport, getHealthReport, scheduleFollowUp } from '../api.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBox from '../components/ErrorBox.jsx'

/* ------------------------------------------------------------------
 *  Farmer View
 *
 *  Single-page flow:
 *    1. Choose a photo
 *    2. Upload to POST /health-reports
 *    3. Show AI prediction, risk, advisory, evidence, explanation
 *    4. Optionally schedule a follow-up
 *
 *  Farm / crop-season IDs are hardcoded for the demo.
 *  In production these would be dropdowns backed by GET /farms,
 *  GET /crop-seasons.
 * ------------------------------------------------------------------ */

const DEMO_FARM_ID = 1
const DEMO_CROP_SEASON_ID = 1

export default function FarmerView() {

  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  // Follow-up form
  const [followUpDate, setFollowUpDate] = useState('')
  const [followUpNotes, setFollowUpNotes] = useState('')
  const [followUpStatus, setFollowUpStatus] = useState(null)

  useEffect(() => {
    if (!file) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) {
      setError('Please choose a photo first.')
      return
    }
    setSubmitting(true)
    setError(null)
    setResult(null)
    setFollowUpStatus(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const { data } = await createHealthReport(formData, {
            params: {
            farm_id: DEMO_FARM_ID,
            crop_season_id: DEMO_CROP_SEASON_ID,
                    },
            })

      // The POST returns a summary — fetch the full report for detail
      const reportId = data.health_report.id
      const { data: fullReport } = await getHealthReport(reportId)

      setResult(fullReport)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Something went wrong during analysis.'
      )
    } finally {
      setSubmitting(false)
    }
  }

  async function handleFollowUp(e) {
    e.preventDefault()
    if (!result || !followUpDate) return

    setFollowUpStatus('submitting')
    try {
      await scheduleFollowUp(result.health_report.id, {
        scheduled_date: followUpDate,
        farmer_notes: followUpNotes || null,
      })
      setFollowUpStatus('done')
      setFollowUpDate('')
      setFollowUpNotes('')
    } catch (err) {
      setFollowUpStatus('error')
    }
  }

  function reset() {
    setFile(null)
    setResult(null)
    setError(null)
    setFollowUpStatus(null)
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">

      <header>
        <h1 className="text-2xl font-bold mb-1">🌱 Farmer</h1>
        <p className="text-slate-400 text-sm">
          Upload a leaf photo. Get a diagnosis, environmental risk,
          and a sourced advisory in seconds.
        </p>
      </header>

      {!result && (
        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-slate-800 bg-slate-900 p-6 space-y-4"
        >
          <label className="block">
            <span className="block text-sm font-medium mb-2">
              Leaf photo
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-slate-300
                         file:mr-3 file:py-2 file:px-4
                         file:rounded file:border-0
                         file:bg-emerald-600 file:text-white
                         hover:file:bg-emerald-500
                         file:cursor-pointer cursor-pointer
                         bg-slate-950 border border-slate-800 rounded-md p-2"
            />
          </label>

          {preview && (
            <div className="rounded-md overflow-hidden border border-slate-800">
              <img
                src={preview}
                alt="preview"
                className="max-h-64 w-full object-contain bg-slate-950"
              />
            </div>
          )}

          <ErrorBox message={error} />

          <button
            type="submit"
            disabled={!file || submitting}
            className="w-full py-2 rounded-md font-medium
                       bg-emerald-600 hover:bg-emerald-500
                       disabled:bg-slate-700 disabled:cursor-not-allowed
                       text-white transition"
          >
            {submitting ? 'Analyzing…' : 'Analyze leaf'}
          </button>
        </form>
      )}

      {submitting && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
          <LoadingSpinner label="Running AI + weather + risk + advisory pipeline…" />
        </div>
      )}

      {result && (
        <ResultCard result={result} onReset={reset} />
      )}

      {result && (
        <form
          onSubmit={handleFollowUp}
          className="rounded-lg border border-slate-800 bg-slate-900 p-6 space-y-3"
        >
          <h2 className="font-semibold">📅 Schedule a follow-up</h2>
          <p className="text-xs text-slate-400">
            We'll compare the next photo against this report to
            detect change over time.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="block text-xs text-slate-400 mb-1">
                Date
              </span>
              <input
                type="date"
                value={followUpDate}
                onChange={(e) => setFollowUpDate(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800
                           rounded-md px-3 py-2 text-sm"
              />
            </label>
            <label className="block">
              <span className="block text-xs text-slate-400 mb-1">
                Notes (optional)
              </span>
              <input
                type="text"
                value={followUpNotes}
                onChange={(e) => setFollowUpNotes(e.target.value)}
                placeholder="e.g. check lower leaves"
                className="w-full bg-slate-950 border border-slate-800
                           rounded-md px-3 py-2 text-sm"
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={followUpStatus === 'submitting'}
            className="px-4 py-2 rounded-md text-sm font-medium
                       bg-blue-600 hover:bg-blue-500
                       disabled:bg-slate-700 text-white transition"
          >
            {followUpStatus === 'submitting'
              ? 'Scheduling…'
              : 'Schedule follow-up'}
          </button>

          {followUpStatus === 'done' && (
            <p className="text-sm text-emerald-400">
              ✓ Follow-up scheduled.
            </p>
          )}
          {followUpStatus === 'error' && (
            <p className="text-sm text-red-400">
              Could not schedule follow-up.
            </p>
          )}
        </form>
      )}

    </div>
  )
}

/* ------------------------------------------------------------------
 *  Result card
 * ------------------------------------------------------------------ */

function ResultCard({ result, onReset }) {
  const prediction = result.prediction
  const risk = result.risk
  const advisory = result.advisory
  const evidence = advisory?.evidence?.[0]
  const explanation = result.explanation
  const escalation = result.escalation

  return (
    <div className="space-y-4">

      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">📋 Result</h2>
        <button
          onClick={onReset}
          className="text-sm text-slate-400 hover:text-slate-200"
        >
          ← Analyze another
        </button>
      </div>

      {/* Prediction */}
      {prediction && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-500 mb-2">
            AI Diagnosis
          </h3>
          <div className="text-2xl font-bold text-emerald-400">
            {prediction.predicted_class}
          </div>
          <div className="text-sm text-slate-400 mt-1">
            Confidence: {(prediction.confidence * 100).toFixed(1)}%
          </div>
        </section>
      )}

      {/* Risk */}
      {risk && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-500 mb-2">
            Environmental risk
          </h3>
          <div className="flex items-baseline gap-3">
            <span className={
              'text-2xl font-bold ' +
              riskColor(risk.risk_level)
            }>
              {risk.risk_level}
            </span>
            <span className="text-slate-400 text-sm">
              {risk.risk_score}/100
            </span>
          </div>
          {risk.factors?.length > 0 && (
            <ul className="mt-3 text-xs text-slate-400 space-y-1">
              {risk.factors.map((f, i) => (
                <li key={i}>
                  • {f.factor.replace(/_/g, ' ')}: +{f.contribution}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* Advisory */}
      {advisory && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-500 mb-3">
            What to do
          </h3>
          <p className="text-slate-200 mb-4">{advisory.advisory_text}</p>

          {advisory.sources && (
            <p className="text-xs text-slate-500">
              Source: {advisory.sources.display_source}
            </p>
          )}
        </section>
      )}

      {/* Evidence */}
      {evidence && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-500 mb-2">
            📚 Evidence
          </h3>
          <p className="text-xs text-slate-400 mb-2">
            {evidence.document_title}
          </p>
          <p className="text-sm text-slate-300 whitespace-pre-line">
            {evidence.chunk_text}
          </p>
        </section>
      )}

      {/* Explanation */}
      {explanation?.text && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-500 mb-2">
            💬 Explanation
          </h3>
          <p className="text-slate-200 leading-relaxed">
            {explanation.text}
          </p>
          <p className="text-xs text-slate-500 mt-2">
            via {explanation.provider}
            {explanation.error ? ` (${explanation.error.slice(0, 60)}…)` : ''}
          </p>
        </section>
      )}

      {/* Escalation */}
      {escalation && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-500 mb-2">
            Escalation
          </h3>
          <div className="font-semibold mb-2">
            {escalationBadge(escalation.decision)}
          </div>
          {escalation.reasons?.length > 0 && (
            <ul className="text-xs text-slate-400 space-y-1">
              {escalation.reasons.map((r, i) => (
                <li key={i}>• {r}</li>
              ))}
            </ul>
          )}
        </section>
      )}

    </div>
  )
}

function riskColor(level) {
  switch ((level || '').toUpperCase()) {
    case 'LOW':      return 'text-emerald-400'
    case 'MODERATE': return 'text-yellow-400'
    case 'HIGH':     return 'text-orange-400'
    case 'CRITICAL': return 'text-red-400'
    default:         return 'text-slate-300'
  }
}

function escalationBadge(decision) {
  switch ((decision || '').toUpperCase()) {
    case 'ROUTINE':       return '⚪ Routine'
    case 'MONITOR':       return '🟡 Monitor'
    case 'ATTENTION':     return '🟠 Attention'
    case 'EXPERT_REVIEW': return '🔴 Expert review'
    default:              return decision
  }
}