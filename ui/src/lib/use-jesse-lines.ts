import { useEffect, useRef, useState } from "react"
import type { ConversationEvent } from "@/lib/api"

const MS_PER_CHAR = 55
const MIN_MS = 1800
const MAX_MS = 9000

export function useJesseLines(
  runId: string | null,
  events: ConversationEvent[] | undefined,
  fresh: boolean,
  replay: boolean,
  voiced: boolean,
) {
  const [line, setLine] = useState<string | null>(null)
  const seen = useRef<Set<string> | null>(null)
  const queue = useRef<string[]>([])
  const timer = useRef<number | null>(null)

  useEffect(() => {
    seen.current = null
    queue.current = []
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = null
    setLine(null)
  }, [runId])

  useEffect(() => () => {
    if (timer.current !== null) window.clearTimeout(timer.current)
  }, [])

  useEffect(() => {
    if (!runId || !events) return
    const lines = events.filter((event) => event.author === "jesse" && event.text.trim())
    if (seen.current === null) seen.current = new Set(fresh ? [] : lines.map((event) => event.id))
    for (const event of lines) {
      if (seen.current.has(event.id)) continue
      seen.current.add(event.id)
      if (replay || (voiced && event.speak)) continue
      queue.current.push(event.text)
    }
    const next = () => {
      const text = queue.current.shift()
      if (text === undefined) {
        timer.current = null
        setLine(null)
        return
      }
      setLine(text)
      timer.current = window.setTimeout(next, Math.min(MAX_MS, Math.max(MIN_MS, text.length * MS_PER_CHAR)))
    }
    if (timer.current === null) next()
  }, [runId, events, fresh, replay, voiced])

  return line
}
