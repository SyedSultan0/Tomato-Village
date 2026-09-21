export default function ErrorBox({ message }) {
  if (!message) return null

  return (
    <div className="my-4 p-4 rounded-md border border-red-900 bg-red-950/50 text-red-200 text-sm">
      <strong className="block mb-1">Something went wrong</strong>
      {typeof message === 'string' ? message : JSON.stringify(message)}
    </div>
  )
}