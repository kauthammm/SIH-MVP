export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      <span className="typing-dot w-2 h-2 bg-emerald-400 rounded-full" />
      <span className="typing-dot w-2 h-2 bg-emerald-400 rounded-full" />
      <span className="typing-dot w-2 h-2 bg-emerald-400 rounded-full" />
      <span className="text-sm text-gray-400 ml-2">Analyzing your field…</span>
    </div>
  )
}
