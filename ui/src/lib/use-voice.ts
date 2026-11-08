import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { api, type VoiceState } from "@/lib/api"
import { BrowserVoice, microphoneError } from "@/lib/browser-voice"

/** Capture this visitor's microphone; submit finalized turns to the existing controller. */
export function useVoice(onRunStarted: (runId: string) => void) {
  const [state, setState] = useState<VoiceState | null>(null)
  const session = useRef<BrowserVoice | null>(null)
  const onRun = useRef(onRunStarted)
  onRun.current = onRunStarted
  const delivery = useRef(Promise.resolve())
  const mounted = useRef(false)

  useEffect(() => {
    mounted.current = true
    let cancelled = false
    api.browserVoice().then(({ available, reason }) => {
      if (cancelled) return
      const supported = window.isSecureContext && typeof navigator.mediaDevices?.getUserMedia === "function" && typeof AudioWorkletNode !== "undefined"
      setState({ available: available && supported,
        reason: supported ? reason : "Use a browser with microphone support over HTTPS.",
        listening: false, pending: false, partial: "", error: null, turns: [] })
    }).catch(() => {
      if (!cancelled) setState({ available: false, reason: "Could not check voice input. Refresh to try again.",
        listening: false, partial: "", error: null, turns: [] })
    })
    return () => {
      cancelled = true
      mounted.current = false
      session.current?.destroy()
      session.current = null
    }
  }, [])

  const submit = useCallback((text: string) => {
    // Serialize turns: a second turn must see the investigation started by the first.
    delivery.current = delivery.current.then(async () => {
      if (!mounted.current) return
      try {
        const turn = await api.voiceTurn(text)
        if (!mounted.current) return
        setState((current) => current && { ...current, turns: [...current.turns, turn].slice(-20) })
        if (turn.action === "started" && turn.run_id) onRun.current(turn.run_id)
        else if (turn.action === "steered") toast.success(`Sent: “${turn.text}”`)
        else toast.error(turn.detail ?? "Your spoken request was not sent.")
      } catch (error) {
        if (mounted.current) toast.error(error instanceof Error ? error.message : "Your spoken request was not sent.")
      }
    })
  }, [])

  const toggle = useCallback(async () => {
    if (session.current) {
      setState((current) => current && { ...current, listening: false, pending: true })
      await session.current.stop()
      return
    }
    if (!state?.available) return
    setState((current) => current && { ...current, pending: true, error: null })
    const capture = new BrowserVoice({
      partial: (partial) => { if (mounted.current) setState((current) => current && { ...current, partial }) },
      turn: submit,
      ready: () => { if (mounted.current) setState((current) => current && { ...current, listening: true, pending: false }) },
      ended: () => {
        if (session.current !== capture) return
        session.current = null
        if (mounted.current) setState((current) => current && { ...current, listening: false, pending: false, partial: "" })
      },
      error: (error) => { if (mounted.current) toast.error(error) },
    })
    session.current = capture
    try {
      await capture.start()
    } catch (error) {
      capture.destroy()
      if (session.current !== capture) return
      session.current = null
      if (mounted.current) {
        setState((current) => current && { ...current, listening: false, pending: false })
        toast.error(microphoneError(error))
      }
    }
  }, [state?.available, submit])

  return { state, toggle }
}
