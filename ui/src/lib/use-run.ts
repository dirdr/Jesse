import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { api, type ConversationEvent, type LiveState, type Snapshot } from "@/lib/api"

const VOICE_KEY = "jesse-voice"
const RUN_PARAM = "run"

function readVoice(): boolean {
  try {
    return localStorage.getItem(VOICE_KEY) === "on"
  } catch {
    return false
  }
}

function runFromUrl(): string | null {
  const id = new URLSearchParams(window.location.search).get(RUN_PARAM)
  return id && /^[a-f0-9]{32}$/.test(id) ? id : null
}

/** One investigation at a time; snapshot and live view are polled while it is active. */
export function useRun() {
  const [runId, setRunId] = useState<string | null>(null)
  const [replay, setReplay] = useState(false)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [live, setLive] = useState<LiveState | null>(null)
  const [report, setReport] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [voiceOn, setVoiceOn] = useState(readVoice)
  const heard = useRef(new Set<string>())
  const voiceRef = useRef(voiceOn)
  voiceRef.current = voiceOn

  const speak = useCallback((events: ConversationEvent[]) => {
    for (const event of events) {
      if (heard.current.has(event.id)) continue
      heard.current.add(event.id)
      if (event.speak && voiceRef.current && "speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(event.text)
        utterance.lang = "en-US"
        window.speechSynthesis.speak(utterance)
      }
    }
  }, [])

  const attach = useCallback(async (id: string, options: { speakHistory: boolean; replay: boolean }) => {
    heard.current = new Set()
    setReport(null)
    setLive(null)
    setReplay(options.replay)
    if (!options.speakHistory) {
      try {
        const first = await api.snapshot(id)
        first.events.forEach((event) => heard.current.add(event.id))
        setSnapshot(first)
      } catch {
        /* polling retries */
      }
    } else {
      setSnapshot(null)
    }
    setRunId(id)
  }, [])

  // Open ?run=<id> as a replay, otherwise resume the controller's active investigation.
  useEffect(() => {
    const requested = runFromUrl()
    if (requested) {
      void attach(requested, { speakHistory: false, replay: true })
      return
    }
    api
      .current()
      .then(({ run_id }) => {
        if (run_id) void attach(run_id, { speakHistory: false, replay: false })
      })
      .catch(() => undefined)
  }, [attach])

  useEffect(() => {
    if (!runId) return
    let cancelled = false
    let timer: number | undefined
    let lastReportKey = ""
    const tick = async () => {
      try {
        const [next, liveState] = await Promise.all([api.snapshot(runId), api.live(runId)])
        if (cancelled) return
        setSnapshot(next)
        setLive(liveState)
        speak(next.events)
        const key = `${next.status}:${next.events.length}`
        if (next.report_url && key !== lastReportKey) {
          lastReportKey = key
          api.report(next.report_url).then((text) => !cancelled && setReport(text)).catch(() => undefined)
        }
        if (next.active) timer = window.setTimeout(tick, 1500)
      } catch (error) {
        console.warn(error)
        if (!cancelled) timer = window.setTimeout(tick, 4000)
      }
    }
    void tick()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [runId, speak])

  const start = useCallback(
    async (question: string) => {
      const text = question.trim()
      if (!text) return false
      setBusy(true)
      try {
        const { run_id } = await api.start(text)
        window.history.replaceState(null, "", window.location.pathname)
        await attach(run_id, { speakHistory: true, replay: false })
        return true
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not start the investigation")
        return false
      } finally {
        setBusy(false)
      }
    },
    [attach],
  )

  /** Corrections from text or a voice adapter (source "voice") reach the live H session. */
  const steer = useCallback(
    async (message: string, source: "text" | "voice" = "text") => {
      const text = message.trim()
      if (!text || !runId) return false
      if (!snapshot?.can_message) {
        toast.info("Corrections open once the simulator session is live.")
        return false
      }
      setBusy(true)
      try {
        await api.message(runId, text, source)
        toast.success("Sent to Jesse. It applies changes between trials.")
        setSnapshot(await api.snapshot(runId))
        return true
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Message not delivered")
        return false
      } finally {
        setBusy(false)
      }
    },
    [runId, snapshot],
  )

  const stop = useCallback(async () => {
    if (!runId) return
    try {
      await api.stop(runId)
      toast("Stopping the experiment. Earlier measurements are kept.")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not stop the run")
    }
  }, [runId])

  const reset = useCallback(() => {
    window.history.replaceState(null, "", window.location.pathname)
    setRunId(null)
    setSnapshot(null)
    setLive(null)
    setReport(null)
    setReplay(false)
  }, [])

  const toggleVoice = useCallback(() => {
    setVoiceOn((on) => {
      const next = !on
      try {
        localStorage.setItem(VOICE_KEY, next ? "on" : "off")
      } catch {
        /* storage unavailable */
      }
      if (!next && "speechSynthesis" in window) window.speechSynthesis.cancel()
      return next
    })
  }, [])

  return { runId, replay, snapshot, live, report, busy, voiceOn, start, steer, stop, reset, toggleVoice }
}
