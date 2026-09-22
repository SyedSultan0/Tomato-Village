import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

// --------------------------------------------------------
//  PASTE YOUR DEMO VIDEO LINK HERE WHEN READY
//
//  Supports:
//    - YouTube URL:   "https://www.youtube.com/watch?v=XXXX"
//    - YouTube short: "https://youtu.be/XXXX"
//    - Direct MP4:    "/demo.mp4"  (place file in frontend/public/)
//    - Leave empty    → modal shows a placeholder
// --------------------------------------------------------
const DEMO_VIDEO_URL = ''

export default function HomeView({ t, lang }) {
  const navigate = useNavigate()
  const [videoOpen, setVideoOpen] = useState(false)

  return (
    <>
      {/* ============================================================
       *  HERO
       * ============================================================ */}
      <header
        className="relative overflow-hidden"
        style={{
          background:
            'radial-gradient(120% 140% at 78% 15%, #2c5540 0%, #1E3B2C 46%, #142a1e 100%)',
          color: 'var(--cream)',
        }}
      >
        <div className="hero-grid">
          {/* Left column */}
          <div>
            <span
              className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-[13px] font-semibold mb-7"
              style={{
                background: 'rgba(216,179,74,0.14)',
                border: '1px solid rgba(216,179,74,0.35)',
                color: 'var(--gold)',
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: 'var(--tomato)' }}
              />
              SIH 2026 · PS 26131
            </span>

            <h1
              className="font-bold"
              style={{
                fontFamily: 'Fraunces, serif',
                fontSize: 'clamp(40px, 6vw, 68px)',
                fontWeight: 600,
                lineHeight: 1.03,
                letterSpacing: '-0.01em',
              }}
            >
              Catching crop
              <br />
              disease{' '}
              <em style={{ fontStyle: 'normal', color: 'var(--green-soft)' }}>
                before
              </em>
              <br />
              it spreads.
            </h1>

            <p
              className="mt-6"
              style={{
                fontSize: 18,
                lineHeight: 1.6,
                color: 'rgba(247,242,231,0.78)',
                maxWidth: 480,
              }}
            >
              Pandora Crop Intelligence pairs an on-field AI diagnosis
              with weather-aware risk scoring and an officer review
              layer — so smallholder farmers get answers that are
              checked, not just guessed.
            </p>

            <div className="hero-actions">
              <button
                className="btn-primary"
                onClick={() => navigate('/farmer')}
              >
                Enter the Prototype
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <a
                href="#portal"
                className="text-[15px] font-semibold transition-colors"
                style={{
                  color: 'var(--cream)',
                  borderBottom: '1px solid rgba(247,242,231,0.35)',
                  paddingBottom: 2,
                }}
              >
                Choose your gate ↓
              </a>
            </div>
          </div>

          {/* Right column — illustration + stat chips */}
          <div className="hero-art">
            <div
              className="stat-chip chip-1"
              style={{
                background: 'rgba(30,59,44,0.9)',
                border: '1px solid rgba(216,179,74,0.3)',
              }}
            >
              <div className="num">8</div>
              <div className="lbl">disease classes detected</div>
            </div>

            <svg viewBox="0 0 400 460" xmlns="http://www.w3.org/2000/svg">
              <ellipse cx="200" cy="430" rx="150" ry="18" fill="#142a1e" />
              <path d="M200 420V180" stroke="#4E7A57" strokeWidth="10" strokeLinecap="round" />
              <path d="M200 260c-40-10-70-45-72-90 45 5 78 35 90 75" fill="#547C5A" />
              <path d="M200 220c40-8 72-40 76-84-46 3-80 32-94 70" fill="#3F6B4A" />
              <path d="M200 330c-46-6-82-40-88-88 50 2 88 32 104 74" fill="#4E7A57" />
              <path d="M200 300c44-6 78-38 84-84-48 2-84 30-100 70" fill="#3F6B4A" />
              <circle cx="150" cy="150" r="28" fill="#C1442D" />
              <circle cx="150" cy="150" r="28" fill="url(#g1)" />
              <path d="M140 128c4-8 14-10 20-6" stroke="#4E7A57" strokeWidth="4" strokeLinecap="round" fill="none" />
              <circle cx="252" cy="128" r="34" fill="#C1442D" />
              <circle cx="252" cy="128" r="34" fill="url(#g2)" />
              <path d="M238 100c5-10 18-12 26-7" stroke="#4E7A57" strokeWidth="4" strokeLinecap="round" fill="none" />
              <circle cx="215" cy="205" r="20" fill="#D8B34A" />
              <defs>
                <radialGradient id="g1" cx="0.35" cy="0.3" r="0.8">
                  <stop offset="0" stopColor="#E0654A" />
                  <stop offset="1" stopColor="#8F3121" />
                </radialGradient>
                <radialGradient id="g2" cx="0.35" cy="0.3" r="0.8">
                  <stop offset="0" stopColor="#E0654A" />
                  <stop offset="1" stopColor="#8F3121" />
                </radialGradient>
              </defs>
            </svg>

            <div
              className="stat-chip chip-2"
              style={{
                background: 'rgba(30,59,44,0.9)',
                border: '1px solid rgba(216,179,74,0.3)',
              }}
            >
              <div className="num">75%</div>
              <div className="lbl">of prototype built so far</div>
            </div>
          </div>
        </div>

        {/* ============================================================
         *  FLOATING DEMO VIDEO CARD
         * ============================================================ */}
        <button
          type="button"
          onClick={() => setVideoOpen(true)}
          className="demo-card"
          aria-label="Watch demo video"
        >
          <span className="demo-thumb">
            <svg viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="11" fill="#F7F2E7" />
              <path d="M10 8.3l6.5 3.7-6.5 3.7v-7.4Z" fill="#1E3B2C" />
            </svg>
          </span>
          <span className="demo-text">
            <span className="demo-title">From Leaf to Advisory</span>
            <span className="demo-sub">Watch the 2-min demo</span>
          </span>
        </button>

        {/* Wave divider */}
        <svg
          className="block w-full mt-16"
          viewBox="0 0 1440 90"
          preserveAspectRatio="none"
          style={{ height: 60 }}
        >
          <path
            d="M0,40 C240,90 480,0 720,30 C960,60 1200,10 1440,50 L1440,90 L0,90 Z"
            fill="#F7F2E7"
          />
        </svg>
      </header>

      {/* ============================================================
       *  TRUST STRIP
       * ============================================================ */}
      <div
        className="py-6 border-b"
        style={{ background: 'var(--cream)', borderColor: 'var(--cream-dim)' }}
      >
        <div className="wrap">
          <div
            className="flex flex-wrap gap-x-10 gap-y-3 justify-center items-center text-[13px] tracking-wide"
            style={{ color: 'var(--soil)', opacity: 0.72 }}
          >
            <span>Weather data — Open-Meteo</span>
            <span>Advisory grounded in ICAR &amp; KVK sources</span>
            <span>Confidence-aware AI — escalates when unsure</span>
            <span>Built for Maharashtra smallholder farms</span>
          </div>
        </div>
      </div>

      {/* ============================================================
       *  PORTAL / SIGNPOST SECTION
       * ============================================================ */}
      <section id="portal" className="py-24 md:py-28" style={{ background: 'var(--cream)' }}>
        <div className="wrap">
          <div className="max-w-[600px] mx-auto mb-16 text-center">
            <span className="section-kicker">Choose your gate</span>
            <h2
              className="font-bold"
              style={{
                fontFamily: 'Fraunces, serif',
                fontSize: 'clamp(30px, 4vw, 44px)',
                color: 'var(--soil)',
              }}
            >
              Three ways into the field
            </h2>
            <p
              className="mt-4"
              style={{ fontSize: 16, color: '#6b5c4c', lineHeight: 1.6 }}
            >
              The prototype branches by who's holding the phone. Pick
              the one you want to walk through — each leads to a
              different view of the same disease data.
            </p>
          </div>

          <div className="portal-signpost">
            <PortalCard
              to="/farmer"
              icon="farmer"
              title="Farmer"
              desc="Snap a leaf photo, get a diagnosis, a risk score, and a plain-language advisory — in the field, in seconds."
              cta="Open farmer view"
            />
            <PortalCard
              to="/officer"
              icon="officer"
              title="Officer"
              desc="Review low-confidence cases the model escalated, confirm or correct them, and feed the outcome back into the system."
              cta="Open officer view"
            />
            <PortalCard
              to="/map"
              icon="hotspot"
              title="Hotspot Map"
              desc="See where disease cases are clustering across the region, weighted by weather-driven risk, updated as reports come in."
              cta="Open hotspot map"
            />
          </div>
        </div>
      </section>

      {/* ============================================================
       *  HOW IT WORKS — 5 steps
       * ============================================================ */}
      <section
        id="how"
        className="py-24"
        style={{ background: 'var(--soil)', color: 'var(--cream)' }}
      >
        <div className="wrap">
          <div className="max-w-[520px] mb-14">
            <span
              className="font-semibold text-sm"
              style={{ color: 'var(--gold)' }}
            >
              How it works
            </span>
            <h2
              className="mt-3"
              style={{
                fontFamily: 'Fraunces, serif',
                fontSize: 'clamp(28px, 4vw, 40px)',
                color: 'var(--cream)',
              }}
            >
              From leaf to advisory in five steps
            </h2>
          </div>

          <div className="flow-steps">
            <FlowStep n="01" title="Photo & GPS" desc="Farmer uploads a leaf photo; location is captured for local weather lookup." />
            <FlowStep n="02" title="AI diagnosis" desc="Classifier reads the leaf and returns a disease class with a confidence score." />
            <FlowStep n="03" title="Risk scoring" desc="Live weather is matched against disease-specific risk profiles for a 0–100 score." />
            <FlowStep n="04" title="Monitoring" desc="Each report is compared to prior ones from the same farm to detect change over time." />
            <FlowStep n="05" title="Escalate or advise" desc="Confident, low-risk cases get a sourced advisory. Serious cases route to an officer for review." />
          </div>
        </div>
      </section>

      {/* ============================================================
       *  DEMO VIDEO MODAL
       * ============================================================ */}
      {videoOpen && (
        <div
          className="video-modal-backdrop"
          onClick={() => setVideoOpen(false)}
        >
          <div
            className="video-modal-inner"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="video-close"
              onClick={() => setVideoOpen(false)}
              aria-label="Close"
            >
              ×
            </button>

            <div className="video-frame">
              <VideoFrame url={DEMO_VIDEO_URL} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}

/* ============================================================
 *  PORTAL CARD
 * ============================================================ */

function PortalCard({ to, icon, title, desc, cta }) {
  const navigate = useNavigate()

  const tint = {
    farmer:  { bg: 'rgba(63,107,74,0.14)',  color: 'var(--green-mid)' },
    officer: { bg: 'rgba(74,53,38,0.12)',   color: 'var(--soil)' },
    hotspot: { bg: 'rgba(193,68,45,0.13)',  color: 'var(--tomato-deep)' },
  }[icon]

  const linkColor = {
    farmer:  'var(--green-mid)',
    officer: 'var(--soil)',
    hotspot: 'var(--tomato-deep)',
  }[icon]

  return (
    <button onClick={() => navigate(to)} className="portal-post">
      <span className="portal-peg" />
      <div
        className="rounded-2xl flex items-center justify-center mb-5"
        style={{
          background: tint.bg,
          color: tint.color,
          width: 52,
          height: 52,
        }}
      >
        <PortalIcon name={icon} />
      </div>
      <h3
        className="text-xl mb-2.5"
        style={{ fontFamily: 'Fraunces, serif', color: 'var(--soil)' }}
      >
        {title}
      </h3>
      <p
        className="text-[14.5px] leading-relaxed mb-5"
        style={{ color: '#6b5c4c', minHeight: 66 }}
      >
        {desc}
      </p>
      <span
        className="inline-flex items-center gap-2 font-semibold text-sm pb-0.5"
        style={{ color: linkColor, borderBottom: `1px solid ${linkColor}` }}
      >
        {cta}
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
          <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </button>
  )
}

function PortalIcon({ name }) {
  if (name === 'farmer') {
    return (
      <svg viewBox="0 0 24 24" fill="none" width="26" height="26">
        <path d="M12 21c4-3 7-6.5 7-11a7 7 0 1 0-14 0c0 4.5 3 8 7 11Z" stroke="currentColor" strokeWidth="1.6" />
        <circle cx="12" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    )
  }
  if (name === 'officer') {
    return (
      <svg viewBox="0 0 24 24" fill="none" width="26" height="26">
        <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" width="26" height="26">
      <path d="M12 21s7-7.1 7-12a7 7 0 1 0-14 0c0 4.9 7 12 7 12Z" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="9" r="2.4" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

/* ============================================================
 *  FLOW STEP
 * ============================================================ */

function FlowStep({ n, title, desc }) {
  return (
    <div
      className="pl-4"
      style={{ borderLeft: '2px solid rgba(216,179,74,0.4)' }}
    >
      <div
        className="mb-2.5"
        style={{
          fontFamily: 'Fraunces, serif',
          fontSize: 15,
          color: 'var(--gold)',
        }}
      >
        {n}
      </div>
      <h4
        className="font-semibold mb-2"
        style={{ fontSize: 16, color: 'var(--cream)' }}
      >
        {title}
      </h4>
      <p
        style={{
          fontSize: 13.5,
          color: 'rgba(247,242,231,0.65)',
          lineHeight: 1.55,
        }}
      >
        {desc}
      </p>
    </div>
  )
}

/* ============================================================
 *  VIDEO FRAME RENDERER
 * ============================================================ */

function VideoFrame({ url }) {
  if (!url) {
    return (
      <div className="video-placeholder">
        <svg viewBox="0 0 24 24" fill="none" width="34" height="34">
          <path d="M23 7l-7 5 7 5V7Z" stroke="#F7F2E7" strokeWidth="1.6" strokeLinejoin="round" />
          <rect x="1" y="5" width="15" height="14" rx="2" stroke="#F7F2E7" strokeWidth="1.6" />
        </svg>
        <p>Demo video coming soon</p>
        <span>
          The full walkthrough — leaf upload, diagnosis, officer review,
          hotspot map — will appear here.
        </span>
      </div>
    )
  }

  const ytMatch = url.match(
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([A-Za-z0-9_-]{6,})/
  )

  if (ytMatch) {
    const videoId = ytMatch[1]
    return (
      <iframe
        src={`https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`}
        title="Pandora demo"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        style={{ width: '100%', height: '100%', border: 0 }}
      />
    )
  }

  return (
    <video controls autoPlay playsInline style={{ width: '100%', height: '100%' }}>
      <source src={url} type="video/mp4" />
    </video>
  )
}