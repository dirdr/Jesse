import { useCallback, useEffect, useState } from "react"
import { api, type ResearchNote, type RunSummary } from "@/lib/api"

/** Past investigations and the research notes Jesse reads, for the sidebar. */
export function useHistory(refreshKey: string | null) {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [notes, setNotes] = useState<ResearchNote[]>([])

  const refresh = useCallback(() => {
    api
      .runs()
      .then(({ runs }) => setRuns(runs))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    api
      .research()
      .then(({ notes }) => setNotes(notes))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 5000)
    return () => window.clearInterval(timer)
  }, [refresh, refreshKey])

  return { runs, notes, refresh }
}
