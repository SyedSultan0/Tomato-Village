import { useState, useEffect } from 'react'
import {
  createHealthReport,
  getHealthReport,
  scheduleFollowUp,
} from '../api.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBox from '../components/ErrorBox.jsx'
import SpeakButton from '../components/SpeakButton.jsx'

const DEMO_FARM_ID = 1
const DEMO_CROP_SEASON_ID = 1

export default function FarmerView({ t, lang }) {

  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const [followUpDate, setFollowUpDate] = useState('')
  const [followUpNotes, setFollowUpNotes] = useState('')
  const [followUpStatus, setFollowUpStatus] = useState(null)

  useEffect(() => {
    if (!file) { setPreview(null); return }
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
    <div className="max-w-3xl mx-auto px-4 py-6 md:py-10 space-y-6">

      <header>
        <h1 className="text-2xl md:text-3xl font-bold text-stone-800">
          🌱 {t.farmerHeading}
        </h1>
        <p className="text-stone-500 text-sm mt-1">
          {t.farmerSub}
        </p>
      </header>

      {!result && (
        <form onSubmit={handleSubmit} className="card p-5 md:p-6 space-y-4">
          <label className="block">
            <span className="block text-sm font-medium text-stone-700 mb-2">
              {t.leafPhoto}
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-stone-600
                         file:mr-3 file:py-2 file:px-4
                         file:rounded-full file:border-0
                         file:bg-emerald-600 file:text-white
                         hover:file:bg-emerald-700
                         file:cursor-pointer cursor-pointer
                         bg-stone-50 border border-stone-200 rounded-xl p-2"
            />
          </label>

          {preview && (
            <div className="rounded-xl overflow-hidden border border-stone-200">
              <img
                src={preview}
                alt="preview"
                className="max-h-72 w-full object-contain bg-stone-50"
              />
            </div>
          )}

          <ErrorBox message={error} />

          <button
            type="submit"
            disabled={!file || submitting}
            className="w-full py-3 rounded-full font-medium
                       bg-emerald-600 hover:bg-emerald-700
                       disabled:bg-stone-300 disabled:cursor-not-allowed
                       text-white transition shadow-sm"
          >
            {submitting ? t.analyzing : t.analyzeLeaf}
          </button>
        </form>
      )}

      {submitting && (
        <div className="card p-6">
          <LoadingSpinner label={t.analyzing} />
        </div>
      )}

      {result && (
        <ResultCard result={result} onReset={reset} t={t} lang={lang} />
      )}

      {result && (
        <form onSubmit={handleFollowUp} className="card p-5 md:p-6 space-y-3">
          <h2 className="font-semibold text-stone-800">
            📅 {t.scheduleFollowUp}
          </h2>
          <p className="text-xs text-stone-500">
            {t.followUpSub}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="block text-xs text-stone-500 mb-1">
                {t.date}
              </span>
              <input
                type="date"
                value={followUpDate}
                onChange={(e) => setFollowUpDate(e.target.value)}
                required
                className="w-full bg-stone-50 border border-stone-200
                           rounded-xl px-3 py-2 text-sm focus:outline-none
                           focus:border-emerald-500"
              />
            </label>
            <label className="block">
              <span className="block text-xs text-stone-500 mb-1">
                {t.notesOptional}
              </span>
              <input
                type="text"
                value={followUpNotes}
                onChange={(e) => setFollowUpNotes(e.target.value)}
                placeholder="e.g. check lower leaves"
                className="w-full bg-stone-50 border border-stone-200
                           rounded-xl px-3 py-2 text-sm focus:outline-none
                           focus:border-emerald-500"
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={followUpStatus === 'submitting'}
            className="px-5 py-2 rounded-full text-sm font-medium
                       bg-blue-600 hover:bg-blue-700
                       disabled:bg-stone-300 text-white transition shadow-sm"
          >
            {followUpStatus === 'submitting'
              ? t.submitting
              : t.scheduleBtn}
          </button>

          {followUpStatus === 'done' && (
            <p className="text-sm text-emerald-600">{t.scheduled}</p>
          )}
          {followUpStatus === 'error' && (
            <p className="text-sm text-red-600">
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

function ResultCard({ result, onReset, t, lang }) {

  const prediction = result.prediction
  const risk = result.risk
  const advisory = result.advisory
  const evidence = advisory?.evidence?.[0]
  const explanation = result.explanation
  const escalation = result.escalation

  return (
    <div className="space-y-4">

      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-stone-800">
          📋 {t.aiDiagnosis}
        </h2>
        <button
          onClick={onReset}
          className="text-sm text-stone-500 hover:text-stone-800"
        >
          {t.analyzedOne}
        </button>
      </div>

      {prediction && (
        <section className="card p-5">
          <div className="text-xs uppercase tracking-wide text-stone-400 mb-2">
            {t.aiDiagnosis}
          </div>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-2xl font-bold text-emerald-700">
                {prediction.predicted_class}
              </div>
              <div className="text-sm text-stone-500 mt-1">
                {t.confidence}: {(prediction.confidence * 100).toFixed(1)}%
              </div>
            </div>
            <SpeakButton
              text={`${prediction.predicted_class}. ${t.confidence} ${(prediction.confidence * 100).toFixed(0)} percent.`}
              lang={lang}
            />
          </div>
        </section>
      )}

      {risk && (
        <section className="card p-5">
          <div className="flex items-start justify-between mb-2">
            <div className="text-xs uppercase tracking-wide text-stone-400">
              {t.environmentalRisk}
            </div>
          </div>
          <div className="flex items-baseline gap-3">
            <span className={'text-2xl font-bold ' + riskColor(risk.risk_level)}>
              {risk.risk_level}
            </span>
            <span className="text-stone-500 text-sm">
              {risk.risk_score}/100
            </span>
          </div>
          {risk.factors?.length > 0 && (
            <ul className="mt-3 text-xs text-stone-500 space-y-1">
              {risk.factors.map((f, i) => (
                <li key={i}>
                  • {f.factor.replace(/_/g, ' ')}:{' '}
                  <span className="text-emerald-600">+{f.contribution}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {advisory && (
        <section className="card p-5">
          <div className="flex items-start justify-between mb-3">
            <div className="text-xs uppercase tracking-wide text-stone-400">
              {t.whatToDo}
            </div>
            <SpeakButton text={advisory.advisory_text} lang={lang} />
          </div>
          <p className="text-stone-700 leading-relaxed">
            {advisory.advisory_text}
          </p>
          {advisory.sources && (
            <p className="text-xs text-stone-400 mt-3">
              {t.source}: {advisory.sources.display_source}
            </p>
          )}
        </section>
      )}

      {evidence && (
        <section className="card p-5">
          <div className="flex items-start justify-between mb-2">
            <div className="text-xs uppercase tracking-wide text-stone-400">
              📚 {t.evidence}
            </div>
            <SpeakButton text={evidence.chunk_text} lang={lang} size="sm" />
          </div>
          <p className="text-xs text-stone-500 mb-2">
            {evidence.document_title}
          </p>
          <p className="text-sm text-stone-600 whitespace-pre-line">
            {evidence.chunk_text}
          </p>
        </section>
      )}

      {explanation?.text && (
        <section className="card p-5">
          <div className="flex items-start justify-between mb-2">
            <div className="text-xs uppercase tracking-wide text-stone-400">
              💬 {t.explanation}
            </div>
            <SpeakButton text={explanation.text} lang={lang} />
          </div>
          <p className="text-stone-700 leading-relaxed">
            {explanation.text}
          </p>
          <p className="text-xs text-stone-400 mt-2">
            {t.via} {explanation.provider}
          </p>
        </section>
      )}

      {escalation && (
        <section className="card p-5">
          <div className="text-xs uppercase tracking-wide text-stone-400 mb-2">
            {t.escalation}
          </div>
          <div className="font-semibold mb-2 text-stone-800">
            {escalationBadge(escalation.decision)}
          </div>
          {escalation.reasons?.length > 0 && (
            <ul className="text-xs text-stone-500 space-y-1">
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
    case 'LOW':      return 'text-emerald-600'
    case 'MODERATE': return 'text-yellow-600'
    case 'HIGH':     return 'text-orange-600'
    case 'CRITICAL': return 'text-red-600'
    default:         return 'text-stone-700'
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