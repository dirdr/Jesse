import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"
import { api, type LiveState, type Snapshot } from "@/lib/api"

const RUN_PARAM = "run"
export const RUN_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/

function runFromUrl(): string | null {
  const id = new URLSearchParams(window.location.search).get(RUN_PARAM)
  return id && RUN_ID.test(id) ? id : null
}

/** One investigation at a time; snapshot and live view are polled while it is active. */
export function useRun() {
  const [runId, setRunId] = useState<string | null>(null)
  const [replay, setReplay] = useState(false)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [live, setLive] = useState<LiveState | null>(null)
  const [report, setReport] = useState<string | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)
  const [reportAttempt, setReportAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  /** True when the run was started from this page: its announcements are new and may be spoken. */
  const [fresh, setFresh] = useState(false)
  const attach = useCallback((id: string, replayMode: boolean, startedHere = false) => {
    setFresh(startedHere)
    setReport(null)
    setReportError(null)
    setLive(null)
    setSnapshot(null)
    setReplay(replayMode)
    setRunId(id)
  }, [])

  // Open ?run=<id> as a replay, otherwise resume the controller's investigation only while it is still running.
  useEffect(() => {
    const requested = runFromUrl()
    if (requested) {
      attach(requested, true)
      return
    }
    api
      .current()
      .then(async ({ run_id }) => {
        if (run_id) attach(run_id, !(await api.snapshot(run_id)).active)
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
        const [stateResult, liveResult] = await Promise.allSettled([api.snapshot(runId), api.live(runId)])
        if (cancelled) return
        if (stateResult.status === "rejected") throw stateResult.reason
        const next = stateResult.value
        setSnapshot(next)
        if (liveResult.status === "fulfilled") setLive(liveResult.value)
        else console.warn("Could not refresh agent screen", liveResult.reason)
        const key = next.report_revision ?? `${next.status}:${next.events.length}`
        if (next.report_url && key !== lastReportKey) {
          try {
            const text = await api.report(next.report_url)
            if (cancelled) return
            if (!text.trim()) throw new Error("The report is empty. Retrying…")
            setReport(text)
            setReportError(null)
            lastReportKey = key
          } catch (error) {
            if (cancelled) return
            setReportError(error instanceof Error ? error.message : "Could not load the report")
          }
        }
        if (next.active || (next.report_url && key !== lastReportKey)) timer = window.setTimeout(tick, next.active ? 1500 : 4000)
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
  }, [runId, reportAttempt])

  const retryReport = useCallback(() => setReportAttempt((attempt) => attempt + 1), [])

  const start = useCallback(
    async (question: string) => {
      const text = question.trim()
      if (!text) return false
      setBusy(true)
      try {
        const { run_id } = await api.start(text)
        window.history.replaceState(null, "", window.location.pathname)
        attach(run_id, false, true)
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

  const startFollowUp = useCallback(async (question: string) => {
    if (!question.trim() || !runId) return false
    // The user explicitly chooses to end this session when launching a follow-up.
    if (snapshot?.active) {
      setBusy(true)
      try {
        await api.stop(runId)
        const deadline = Date.now() + 30000
        while ((await api.snapshot(runId)).active) {
          if (Date.now() >= deadline) throw new Error("The previous session is still closing. Try again shortly.")
          await new Promise((resolve) => window.setTimeout(resolve, 500))
        }
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not close the previous session")
        return false
      } finally {
        setBusy(false)
      }
    }
    return start(question)
  }, [runId, snapshot?.active, start])

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
    setReportError(null)
    setReplay(false)
  }, [])

  return { runId, replay, snapshot, live, report, reportError, retryReport, busy, fresh, start, startFollowUp, steer, stop, reset, attach }
}
