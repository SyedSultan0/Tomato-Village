import { useEffect, useState } from 'react'
import {
  getOfficerQueue,
  getHealthReport,
  submitExpertValidation,
} from '../api.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBox from '../components/ErrorBox.jsx'

/* ------------------------------------------------------------------
 *  OfficerView
 *
 *  Two panels:
 *    - Left  : pending queue (severity-sorted, from GET /expert-review/queue)
 *    - Right : full detail of the selected case + verdict form
 *
 *  Submitting a verdict removes the case from the queue and shows it
 *  in the "recently reviewed" section until the page is refreshed.
 * ------------------------------------------------------------------ */

const DEMO_EXPERT_ID = 1

const VERDICT_OPTIONS = [
  { value: 'CONFIRMED',    label: '✅ Confirmed (agree with AI)' },
  { value: 'CORRECTED',    label: '✏️ Corrected (different condition)' },
  { value: 'REJECTED',     label: '❌ Rejected (AI is wrong)' },
  { value: 'INCONCLUSIVE', label: '❓ Inconclusive (need more info)' },
]

export default function OfficerView() {

  const [queue, setQueue] = useState([])
  const [loadingQueue, setLoadingQueue] = useState(true)
  const [queueError, setQueueError] = useState(null)

  const [selectedId, setSelectedId] = useState(null)
  const [report, setReport] = useState(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [reportError, setReportError] = useState(null)

  const [justReviewed, setJustReviewed] = useState([])

  // Load queue on mount
  useEffect(() => {
    loadQueue()
  }, [])

  async function loadQueue() {
    setLoadingQueue(true)
    setQueueError(null)
    try {
      const { data } = await getOfficerQueue({ limit: 50 })
      setQueue(data.items || [])
    } catch (err) {
      setQueueError(
        err.response?.data?.detail || err.message || 'Failed to load queue.'
      )
    } finally {
      setLoadingQueue(false)
    }
  }

  async function selectCase(reportId) {
    if (reportId === selectedId) return
    setSelectedId(reportId)
    setReport(null)
    setReportError(null)
    setLoadingReport(true)
    try {
      const { data } = await getHealthReport(reportId)
      setReport(data)
    } catch (err) {
      setReportError(
        err.response?.data?.detail || err.message || 'Failed to load report.'
      )
    } finally {
      setLoadingReport(false)
    }
  }

  function handleReviewed(reportId, verdict) {
    // Remove from queue, add to "recently reviewed"
    const item = queue.find((q) => q.health_report_id === reportId)
    setQueue((prev) => prev.filter((q) => q.health_report_id !== reportId))
    if (item) {
      setJustReviewed((prev) => [{ ...item, verdict }, ...prev])
    }
    setSelectedId(null)
    setReport(null)
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-4">

      <header>
        <h1 className="text-2xl font-bold mb-1">👮 Officer</h1>
        <p className="text-slate-400 text-sm">
          Review flagged cases and submit verdicts. Cases are
          sorted by severity, newest first.
        </p>
      </header>

      <ErrorBox message={queueError} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Left: queue */}
        <div className="lg:col-span-1 space-y-3">
          <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-sm uppercase tracking-wide text-slate-500 mb-3">
              Pending queue
            </h2>

            {loadingQueue ? (
              <LoadingSpinner label="Loading queue…" />
            ) : queue.length === 0 ? (
              <p className="text-sm text-slate-500">
                Nothing waiting for review. ✓
              </p>
            ) : (
              <ul className="space-y-2">
                {queue.map((item) => (
                  <QueueItem
                    key={item.health_report_id}
                    item={item}
                    selected={item.health_report_id === selectedId}
                    onSelect={() => selectCase(item.health_report_id)}
                  />
                ))}
              </ul>
            )}
          </section>

          {justReviewed.length > 0 && (
            <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <h2 className="text-sm uppercase tracking-wide text-slate-500 mb-3">
                Reviewed this session
              </h2>
              <ul className="space-y-2">
                {justReviewed.map((item) => (
                  <li
                    key={item.health_report_id}
                    className="text-xs text-slate-400 flex items-center justify-between"
                  >
                    <span>#{item.health_report_id} · {item.prediction?.predicted_class}</span>
                    <span className="text-emerald-500">{item.verdict}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        {/* Right: detail */}
        <div className="lg:col-span-2">
          {!selectedId ? (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-8 text-center text-slate-500 text-sm">
              Select a case from the queue to review it.
            </div>
          ) : loadingReport ? (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-8">
              <LoadingSpinner label="Loading report…" />
            </div>
          ) : reportError ? (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-8">
              <ErrorBox message={reportError} />
            </div>
          ) : (
            <ReportDetail
              report={report}
              onReviewed={(verdict) => handleReviewed(selectedId, verdict)}
            />
          )}
        </div>

      </div>

    </div>
  )
}

/* ------------------------------------------------------------------
 *  Queue item
 * ------------------------------------------------------------------ */

function QueueItem({ item, selected, onSelect }) {
  const risk = item.risk?.risk_level
  const decision = item.escalation?.decision

  return (
    <li>
      <button
        onClick={onSelect}
        className={
          'w-full text-left rounded-md border px-3 py-2 transition ' +
          (selected
            ? 'border-emerald-500 bg-slate-950'
            : 'border-slate-800 bg-slate-950 hover:border-slate-600')
        }
      >
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-slate-500">
            #{item.health_report_id}
          </span>
          <span className={'text-xs font-semibold ' + riskText(risk)}>
            {risk}
          </span>
        </div>
        <div className="text-sm font-medium text-slate-100 truncate">
          {item.prediction?.predicted_class}
        </div>
        <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
          <span>{item.farm?.district || '—'}</span>
          <span className="text-orange-400">
            {decisionLabel(decision)}
          </span>
        </div>
      </button>
    </li>
  )
}

/* ------------------------------------------------------------------
 *  Report detail + verdict form
 * ------------------------------------------------------------------ */

function ReportDetail({ report, onReviewed }) {

  const prediction = report.prediction
  const risk = report.risk
  const advisory = report.advisory
  const evidence = advisory?.evidence?.[0]
  const explanation = report.explanation
  const escalation = report.escalation

  // Verdict form state
  const [status, setStatus] = useState('CONFIRMED')
  const [confirmedCondition, setConfirmedCondition] = useState(
    prediction?.predicted_class || ''
  )
  const [comments, setComments] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  // All the conditions available in your system
  const CONDITION_OPTIONS = [
    'Late Blight',
    'Early Blight',
    'Leaf Miner',
    'Spotted Wilt Virus',
    'Magnesium Deficiency',
    'Nitrogen Deficiency',
    'Potassium Deficiency',
    'Healthy',
  ]

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)

    try {
      const payload = {
        expert_id: DEMO_EXPERT_ID,
        status,
        comments: comments || null,
      }

      // Only send confirmed_condition for CONFIRMED / CORRECTED
      if (status === 'CONFIRMED' || status === 'CORRECTED') {
        payload.confirmed_condition = confirmedCondition
      }

      await submitExpertValidation(report.health_report.id, payload)
      onReviewed(status)
    } catch (err) {
      setSubmitError(
        err.response?.data?.detail || err.message || 'Submission failed.'
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">

      {/* Header */}
      <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs text-slate-500">
              Report #{report.health_report?.id}
            </div>
            <div className="text-xl font-bold text-slate-100 mt-1">
              {prediction?.predicted_class || 'Unknown'}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {report.farm?.farm_name} · {report.farm?.district}
            </div>
          </div>
          {risk && (
            <div className="text-right">
              <div className={'text-lg font-bold ' + riskText(risk.risk_level)}>
                {risk.risk_level}
              </div>
              <div className="text-xs text-slate-500">
                {risk.risk_score}/100
              </div>
            </div>
          )}
        </div>

        {escalation && (
          <div className="mt-3 pt-3 border-t border-slate-800">
            <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">
              Escalation
            </div>
            <div className="font-semibold text-orange-400">
              {decisionLabel(escalation.decision)}
            </div>
            {escalation.reasons?.length > 0 && (
              <ul className="text-xs text-slate-400 mt-1 space-y-0.5">
                {escalation.reasons.map((r, i) => (
                  <li key={i}>• {r}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      {/* Advisory */}
      {advisory && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-500 mb-2">
            Advisory
          </h3>
          <p className="text-slate-200 text-sm">
            {advisory.advisory_text}
          </p>
          {advisory.sources && (
            <p className="text-xs text-slate-500 mt-2">
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
          <p className="text-sm text-slate-300 whitespace-pre-line max-h-64 overflow-y-auto">
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
          <p className="text-slate-200 text-sm">
            {explanation.text}
          </p>
        </section>
      )}

      {/* Verdict form */}
      <section className="rounded-lg border-2 border-emerald-800/60 bg-slate-900 p-5">
        <h3 className="text-sm uppercase tracking-wide text-emerald-400 mb-3">
          Submit verdict
        </h3>

        <form onSubmit={handleSubmit} className="space-y-3">

          <label className="block">
            <span className="block text-xs text-slate-400 mb-1">
              Verdict
            </span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-sm"
            >
              {VERDICT_OPTIONS.map((v) => (
                <option key={v.value} value={v.value}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>

          {(status === 'CONFIRMED' || status === 'CORRECTED') && (
            <label className="block">
              <span className="block text-xs text-slate-400 mb-1">
                {status === 'CONFIRMED'
                  ? 'Confirm the condition'
                  : 'Correct to which condition?'}
              </span>
              <select
                value={confirmedCondition}
                onChange={(e) => setConfirmedCondition(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-sm"
              >
                {CONDITION_OPTIONS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
          )}

          <label className="block">
            <span className="block text-xs text-slate-400 mb-1">
              Comments (optional)
            </span>
            <textarea
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              rows={2}
              placeholder="e.g. Confirmed on field visit."
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-sm"
            />
          </label>

          <ErrorBox message={submitError} />

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2 rounded-md font-medium
                       bg-emerald-600 hover:bg-emerald-500
                       disabled:bg-slate-700 disabled:cursor-not-allowed
                       text-white transition"
          >
            {submitting ? 'Submitting…' : 'Submit verdict'}
          </button>
        </form>
      </section>

    </div>
  )
}

/* ------------------------------------------------------------------
 *  Helpers
 * ------------------------------------------------------------------ */

function riskText(level) {
  switch ((level || '').toUpperCase()) {
    case 'LOW':      return 'text-emerald-400'
    case 'MODERATE': return 'text-yellow-400'
    case 'HIGH':     return 'text-orange-400'
    case 'CRITICAL': return 'text-red-400'
    default:         return 'text-slate-300'
  }
}

function decisionLabel(decision) {
  switch ((decision || '').toUpperCase()) {
    case 'ROUTINE':       return '⚪ Routine'
    case 'MONITOR':       return '🟡 Monitor'
    case 'ATTENTION':     return '🟠 Attention'
    case 'EXPERT_REVIEW': return '🔴 Expert review'
    default:              return decision || '—'
  }
}