import { useCallback, useEffect, useState } from "react"
import { api, type ResearchContext, type RunSummary } from "@/lib/api"

/** Past investigations for the sidebar and the research contexts the launcher suggests. */
export function useHistory(refreshKey: string | null) {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [contexts, setContexts] = useState<ResearchContext[]>([])
  const [pinned, setPinned] = useState<string | null>(null)

  const refresh = useCallback(() => {
    api
      .runs()
      .then(({ runs }) => setRuns(runs))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    api
      .contexts()
      .then(({ pinned, contexts }) => {
        setPinned(pinned)
        setContexts(contexts)
      })
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 5000)
    return () => window.clearInterval(timer)
  }, [refresh, refreshKey])

  return { runs, contexts, pinned, refresh }
}
