import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { api, type VoiceState } from "@/lib/api"

/**
 * The microphone is captured by the local Jesse controller (Gladia). Each finished spoken turn starts a run
 * or steers the active one server-side; this hook mirrors that state and opens runs it started.
 */
export function useVoice(onRunStarted: (runId: string) => void) {
  const [state, setState] = useState<VoiceState | null>(null)
  const seen = useRef<Set<string> | null>(null)
  const onRun = useRef(onRunStarted)
  onRun.current = onRunStarted

  const apply = useCallback((next: VoiceState) => {
    if (seen.current === null) {
      seen.current = new Set(next.turns.map((turn) => turn.id))
    }
    for (const turn of next.turns) {
      if (seen.current.has(turn.id)) continue
      seen.current.add(turn.id)
      if (turn.action === "started" && turn.run_id) {
        onRun.current(turn.run_id)
      } else if (turn.action === "steered") {
        toast.success(`Sent: “${turn.text}”`)
      } else {
        toast.error(turn.detail ?? "Your request was not sent.")
      }
    }
    setState(next)
  }, [])

  useEffect(() => {
    let cancelled = false
    let timer: number | undefined
    const tick = async () => {
      try {
        const next = await api.voice()
        if (cancelled) return
        apply(next)
        timer = window.setTimeout(tick, next.listening ? 400 : 3000)
      } catch {
        if (!cancelled) timer = window.setTimeout(tick, 5000)
      }
    }
    void tick()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [apply])

  const lastError = useRef<string | null>(null)
  useEffect(() => {
    const error = state?.error ?? null
    if (error && error !== lastError.current) toast.error(error)
    lastError.current = error
  }, [state?.error])

  const toggle = useCallback(async () => {
    try {
      apply(await (state?.listening ? api.voiceStop() : api.voiceStart()))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Microphone unavailable")
    }
  }, [apply, state?.listening])

  return { state, toggle }
}
