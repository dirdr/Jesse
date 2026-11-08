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
 * selected persona voice. History is never read aloud automatically: only events that appear after the page attached,
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
  personaId = "pinkman",
  replayAction: Action | null = null,
  replayPlaying = false,
  onReplayBusy?: (busy: boolean) => void,
) {
  const [available, setAvailable] = useState(false)
  const [on, setOn] = useState(readOn)
  const heard = useRef<Set<string> | null>(null)
  const queue = useRef<{ url: string; text: string }[]>([])
  const [speaking, setSpeaking] = useState<string | null>(null)
  const playing = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    let cancelled = false
    api.speechAvailable(runId).then(({ available }) => { if (!cancelled) setAvailable(available) }).catch(() => { if (!cancelled) setAvailable(false) })
    return () => { cancelled = true }
  }, [runId, personaId])

  const silence = useCallback(() => {
    queue.current = []
    toast.dismiss("jesse-audio")
    playing.current?.pause()
    playing.current = null
    setSpeaking(null)
  }, [])

  const blocked = useRef(false)
  const lastEnded = useRef(0)
  const narrated = useRef(-1)
  const narration = useRef<{ runId: string; action: Action | undefined; enabled: boolean } | null>(null)

  const next = useCallback(() => {
    if (playing.current || blocked.current) return
    if (!queue.current.length) {
      const current = narration.current
      const action = current?.action
      if (!current?.enabled || !action || action.index <= narrated.current) {
        setSpeaking(null)
        return
      }
      if (Date.now() - lastEnded.current < NARRATION_GAP_MS) {
        setSpeaking(null)
        return
      }
      narrated.current = action.index
      queue.current.push({ url: api.actionSpeechUrl(current.runId, action.index), text: action.text ?? "" })
    }
    const item = queue.current.shift()!
    const audio = new Audio(item.url)
    playing.current = audio
    const done = () => {
      if (playing.current !== audio) return
      playing.current = null
      lastEnded.current = Date.now()
      next()
    }
    audio.onplaying = () => {
      if (playing.current === audio) setSpeaking(item.text)
    }
    audio.onended = done
    audio.onerror = done
    audio.play().catch((error: unknown) => {
      if (playing.current === audio) playing.current = null
      if (error instanceof DOMException && error.name === "NotAllowedError") {
        // The browser refuses sound until the page is clicked (e.g. after a refresh). Keep the update and resume on click.
        queue.current.unshift(item)
        setSpeaking(null)
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
      ? { runId, action: latestNarratable(actions), enabled: on && available && active && !replay && replayAction === null }
      : null
    next()
  }, [runId, actions, on, available, active, replay, replayAction, next])

  // Narration also needs a clock: the gap can elapse between polls.
  useEffect(() => {
    if (!runId || !active || replay) return
    const timer = window.setInterval(next, 1000)
    return () => window.clearInterval(timer)
  }, [runId, active, replay, replayAction, next])

  useEffect(() => {
    if (!runId || !events) return
    // Announcements and the step the agent is starting, each spoken once.
    const steps = (plan ?? []).flatMap((goal, index) =>
      /run|progress|active/.test(goal.status) ? [{ key: `step:${index}:${goal.title}`, url: api.stepSpeechUrl(runId, index), text: goal.title }] : [],
    )
    const items = [
      ...events.filter((event) => event.speak).map((event) => ({ key: event.id, url: api.speechUrl(runId, event.id), text: event.text })),
      ...steps,
    ]
    if (heard.current === null) {
      // Joining a run already in progress: skip the history but say where it stands now (its latest update).
      heard.current = new Set(fresh ? [] : items.slice(0, -1).map((item) => item.key))
    }
    for (const item of items) {
      if (heard.current.has(item.key)) continue
      heard.current.add(item.key)
      if (on && available && !replay && replayAction === null) queue.current.push({ url: item.url, text: item.text })
    }
    next()
  }, [runId, events, plan, fresh, on, available, replay, replayAction, next])

  // Replay uses the same cached persona audio as live narration. Hold the timeline
  // while audio loads and plays so the next action cannot cut off its sentence.
  const reviewing = replayAction !== null
  useEffect(() => {
    if (replay || reviewing) silence()
    return silence
  }, [replay, reviewing, silence])

  useEffect(() => {
    if (!runId || !replayAction || !replayPlaying || !on || !available) {
      onReplayBusy?.(false)
      return
    }
    if (SILENT_TOOLS.test(replayAction.tool) || !replayAction.text) return
    const audio = new Audio(api.actionSpeechUrl(runId, replayAction.index))
    let cancelled = false
    onReplayBusy?.(true)
    const done = () => {
      if (cancelled) return
      setSpeaking(null)
      onReplayBusy?.(false)
    }
    audio.onplaying = () => { if (!cancelled) setSpeaking(replayAction.text ?? null) }
    audio.onended = done
    audio.onerror = done
    void audio.play().catch(done)
    return () => {
      cancelled = true
      audio.pause()
      setSpeaking(null)
      onReplayBusy?.(false)
    }
  }, [runId, replayAction, replayPlaying, on, available, onReplayBusy])

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

  return { available, on, toggle, speaking }
}
