import { useCallback, useEffect, useRef, useState } from "react"
import { api, type ConversationEvent } from "@/lib/api"

const KEY = "jesse-speech"

function readOn(): boolean {
  try {
    return localStorage.getItem(KEY) !== "off"
  } catch {
    return true
  }
}

/**
 * Plays Jesse's spoken announcements (events with `speak`) one after another, using the controller's
 * OpenAI text-to-speech. History is never read aloud: only events that appear after the page attached,
 * plus everything for a run started from this page.
 */
export function useSpeech(runId: string | null, events: ConversationEvent[] | undefined, fresh: boolean, replay: boolean) {
  const [available, setAvailable] = useState(false)
  const [on, setOn] = useState(readOn)
  const heard = useRef<Set<string> | null>(null)
  const queue = useRef<string[]>([])
  const playing = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    api.speechAvailable().then(({ available }) => setAvailable(available)).catch(() => setAvailable(false))
  }, [])

  const silence = useCallback(() => {
    queue.current = []
    playing.current?.pause()
    playing.current = null
  }, [])

  const next = useCallback(() => {
    if (playing.current || !queue.current.length) return
    const audio = new Audio(queue.current.shift())
    playing.current = audio
    const done = () => {
      if (playing.current === audio) playing.current = null
      next()
    }
    audio.onended = done
    audio.onerror = done
    audio.play().catch(done)
  }, [])

  useEffect(() => {
    heard.current = null
    silence()
  }, [runId, silence])

  useEffect(() => {
    if (!runId || !events) return
    if (heard.current === null) {
      heard.current = new Set(fresh ? [] : events.map((event) => event.id))
    }
    for (const event of events) {
      if (heard.current.has(event.id)) continue
      heard.current.add(event.id)
      if (event.speak && on && available && !replay) queue.current.push(api.speechUrl(runId, event.id))
    }
    next()
  }, [runId, events, fresh, on, available, replay, next])

  const toggle = useCallback(() => {
    setOn((value) => {
      try {
        localStorage.setItem(KEY, value ? "off" : "on")
      } catch {
        /* storage unavailable */
      }
      if (value) silence()
      return !value
    })
  }, [silence])

  return { available: available && !replay, on, toggle }
}
