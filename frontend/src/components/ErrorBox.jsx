export default function ErrorBox({ message }) {
  if (!message) return null
  return (
    <div className="my-4 p-4 rounded-xl border border-red-200 bg-red-50 text-red-800 text-sm">
      <strong className="block mb-1">Something went wrong</strong>
      {typeof message === 'string' ? message : JSON.stringify(message)}
    </div>
  )
}