import { LANGUAGES } from '../i18n.js'

export default function LanguageBar({ lang, onChange }) {
  return (
    <div
      className="flex items-center gap-0.5 rounded-full p-0.5"
      style={{
        border: '1px solid rgba(216, 179, 74, 0.28)',
        background: 'rgba(20, 42, 30, 0.6)',
      }}
    >
      {LANGUAGES.map((l) => {
        const active = lang === l.code
        return (
          <button
            key={l.code}
            onClick={() => onChange(l.code)}
            title={l.label}
            className="px-2.5 py-1 rounded-full text-xs font-medium transition-colors"
            style={{
              background: active ? 'var(--gold)' : 'transparent',
              color: active ? 'var(--soil)' : 'rgba(239, 231, 214, 0.75)',
            }}
          >
            {l.native}
          </button>
        )
      })}
    </div>
  )
}