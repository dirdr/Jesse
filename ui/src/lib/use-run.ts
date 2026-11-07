import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"
import { api, type LiveState, type Snapshot } from "@/lib/api"

const RUN_PARAM = "run"

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
  /** True when the run was started from this page: its announcements are new and may be spoken. */
  const [fresh, setFresh] = useState(false)
  const attach = useCallback((id: string, replayMode: boolean, startedHere = false) => {
    setFresh(startedHere)
    setReport(null)
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
        if (run_id && (await api.snapshot(run_id)).active) attach(run_id, false)
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
  }, [runId])

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

  return { runId, replay, snapshot, live, report, busy, fresh, start, steer, stop, reset, attach }
}
