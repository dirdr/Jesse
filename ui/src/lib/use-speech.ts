import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { api, type Action, type ConversationEvent, type PlanGoal } from "@/lib/api"

const KEY = "jesse-speech"
/** Between announcements, narrate the agent's latest action at most this often. */
const NARRATION_GAP_MS = 6000
const SILENT_TOOLS = /^(message|wait|zoom|screenshot|update_plan|record_|analyze_|answer)/

function latestNarratable(actions: Action[] | undefined): Action | undefined {
  return [...(actions ?? [])].reverse().find((action) => !SILENT_TOOLS.test(action.tool) && action.text)
}

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
export function useSpeech(
  runId: string | null,
  events: ConversationEvent[] | undefined,
  plan: PlanGoal[] | undefined,
  actions: Action[] | undefined,
  active: boolean,
  fresh: boolean,
  replay: boolean,
) {
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
    toast.dismiss("jesse-audio")
    playing.current?.pause()
    playing.current = null
  }, [])

  const blocked = useRef(false)
  const lastEnded = useRef(0)
  const narrated = useRef(-1)
  const narration = useRef<{ runId: string; action: Action | undefined; enabled: boolean } | null>(null)

  const next = useCallback(() => {
    if (playing.current || blocked.current) return
    if (!queue.current.length) {
      // Nothing scheduled: say what the agent is doing now, skipping actions that happened in between.
      const current = narration.current
      const action = current?.action
      if (!current?.enabled || !action || action.index <= narrated.current) return
      if (Date.now() - lastEnded.current < NARRATION_GAP_MS) return
      narrated.current = action.index
      queue.current.push(api.actionSpeechUrl(current.runId, action.index))
    }
    const url = queue.current.shift()!
    const audio = new Audio(url)
    playing.current = audio
    const done = () => {
      if (playing.current === audio) playing.current = null
      lastEnded.current = Date.now()
      next()
    }
    audio.onended = done
    audio.onerror = done
    audio.play().catch((error: unknown) => {
      if (playing.current === audio) playing.current = null
      if (error instanceof DOMException && error.name === "NotAllowedError") {
        // The browser refuses sound until the page is clicked (e.g. after a refresh). Keep the update and resume on click.
        queue.current.unshift(url)
        blocked.current = true
        toast("Click anywhere to hear Jesse", { id: "jesse-audio", duration: Infinity })
        const resume = () => {
          blocked.current = false
          toast.dismiss("jesse-audio")
          next()
        }
        document.addEventListener("pointerdown", resume, { once: true })
        document.addEventListener("keydown", resume, { once: true })
        return
      }
      next()
    })
  }, [])

  useEffect(() => {
    heard.current = null
    narrated.current = -1
    silence()
  }, [runId, silence])

  useEffect(() => {
    narration.current = runId
      ? { runId, action: latestNarratable(actions), enabled: on && available && active && !replay }
      : null
    next()
  }, [runId, actions, on, available, active, replay, next])

  // Narration also needs a clock: the gap can elapse between polls.
  useEffect(() => {
    if (!runId || !active || replay) return
    const timer = window.setInterval(next, 1000)
    return () => window.clearInterval(timer)
  }, [runId, active, replay, next])

  useEffect(() => {
    if (!runId || !events) return
    // Announcements and the step the agent is starting, each spoken once.
    const steps = (plan ?? []).flatMap((goal, index) =>
      /run|progress|active/.test(goal.status) ? [{ key: `step:${index}:${goal.title}`, url: api.stepSpeechUrl(runId, index) }] : [],
    )
    const items = [
      ...events.filter((event) => event.speak).map((event) => ({ key: event.id, url: api.speechUrl(runId, event.id) })),
      ...steps,
    ]
    if (heard.current === null) {
      // Joining a run already in progress: skip the history but say where it stands now (its latest update).
      heard.current = new Set(fresh ? [] : items.slice(0, -1).map((item) => item.key))
    }
    for (const item of items) {
      if (heard.current.has(item.key)) continue
      heard.current.add(item.key)
      if (on && available && !replay) queue.current.push(item.url)
    }
    next()
  }, [runId, events, plan, fresh, on, available, replay, next])

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
