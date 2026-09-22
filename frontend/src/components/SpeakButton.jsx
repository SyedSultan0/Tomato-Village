import { useEffect, useState } from 'react'

const VOICE_LOCALE = {
  en: 'en-IN',
  te: 'te-IN',
  hi: 'hi-IN',
  mr: 'mr-IN',
}

export default function SpeakButton({ text, lang = 'en', size = 'md' }) {
  const [speaking, setSpeaking] = useState(false)
  const [available, setAvailable] = useState(true)

  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      setAvailable(false)
    }
  }, [])

  useEffect(() => {
    // Cancel speech when the text changes or component unmounts
    return () => {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel()
      }
    }
  }, [text])

  function speak() {
    if (!text || !window.speechSynthesis) return

    if (speaking) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
      return
    }

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = VOICE_LOCALE[lang] || 'en-IN'
    utterance.rate = 0.95
    utterance.pitch = 1
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)

    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
    setSpeaking(true)
  }

  if (!available) return null

  const sizeClasses =
    size === 'sm'
      ? 'w-7 h-7 text-sm'
      : 'w-9 h-9 text-base'

  return (
    <button
      type="button"
      onClick={speak}
      title={speaking ? 'Stop' : 'Speak'}
      className={`${sizeClasses} rounded-full flex items-center justify-center
                  border border-stone-200 bg-white text-stone-600
                  hover:bg-stone-50 hover:border-stone-300
                  transition shadow-sm shrink-0`}
    >
      {speaking ? '⏹' : '🔊'}
    </button>
  )
}