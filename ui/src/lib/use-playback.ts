import { useCallback, useEffect, useRef, useState } from "react"
import type { Action } from "@/lib/api"

const STEP_MS = 1600

export function usePlayback(runId: string | null, actions: Action[], onFrame: (frame: number | null) => void) {
  const [focus, setFocus] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const latest = useRef(actions)
  latest.current = actions

  useEffect(() => {
    setFocus(null)
    setPlaying(false)
  }, [runId])

  const select = useCallback(
    (index: number | null) => {
      setFocus(index)
      if (index === null) {
        onFrame(null)
        return
      }
      const frame = latest.current[index]?.frame
      if (frame !== null && frame !== undefined) onFrame(frame)
    },
    [onFrame],
  )

  useEffect(() => {
    if (!playing) return
    const timer = window.setTimeout(
      () => {
        const next = (focus ?? -1) + 1
        if (next >= latest.current.length) {
          setPlaying(false)
          select(null)
        } else {
          select(next)
        }
      },
      focus === null ? 0 : STEP_MS,
    )
    return () => window.clearTimeout(timer)
  }, [playing, focus, select])

  const toggle = useCallback(() => setPlaying((value) => !value), [])

  const release = useCallback(() => {
    setPlaying(false)
    setFocus(null)
  }, [])

  const choose = useCallback(
    (index: number) => {
      setPlaying(false)
      select(index)
    },
    [select],
  )

  const live = useCallback(() => {
    setPlaying(false)
    select(null)
  }, [select])

  return { focus, playing, toggle, choose, live, release }
}
