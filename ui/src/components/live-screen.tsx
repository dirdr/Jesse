import { useEffect, useMemo, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { ChevronLeft, ChevronRight, MonitorPlay, Radio } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { actionStyle, describe, pointOf } from "@/lib/actions"
import { api, type Action, type Frame } from "@/lib/api"


interface LiveScreenProps {
  runId: string
  frames: Frame[]
  actions: Action[]
  active: boolean
  replay: boolean
  pinned: number | null
  focus: number | null
  playing: boolean
  onLive: () => void
  onPin: (index: number | null) => void
}

export function LiveScreen({ runId, frames, actions, active, replay, pinned, focus, playing, onLive, onPin }: LiveScreenProps) {
  const latest = frames.length - 1
  const shown = pinned ?? latest
  const following = pinned === null && focus === null
  const reviewing = !following
  const returnLabel = replay || !active ? "Back to latest" : "Back to live"
  const [loaded, setLoaded] = useState<Set<number>>(() => new Set())

  // Keep showing the last decoded screenshot until the next one is ready, so the view never flashes.
  const [visible, setVisible] = useState<number>(-1)
  useEffect(() => {
    if (shown < 0) return
    if (loaded.has(shown)) {
      setVisible(shown)
      return
    }
    const image = new Image()
    image.onload = () => {
      setLoaded((previous) => new Set(previous).add(shown))
      setVisible(shown)
    }
    image.src = api.frameUrl(runId, shown)
  }, [runId, shown, loaded])

  const frameActions = useMemo(() => {
    const onFrame = actions.filter((action) => action.frame === visible)
    const chosen = focus !== null ? actions[focus] : undefined
    return chosen && chosen.frame === visible ? onFrame.filter((action) => action.index <= chosen.index) : onFrame
  }, [actions, visible, focus])
  const pointer = [...frameActions].reverse().map((action) => ({ action, point: pointOf(action, frames[visible]) })).find((item) => item.point)
  const lastAction = frameActions.at(-1)

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-card px-3 py-2">
        <div role="status" className="flex items-center gap-2 text-sm">
          {reviewing || replay ? <MonitorPlay className="size-4 text-hazard" /> : <Radio className="size-4 text-brand" />}
          <span className="font-semibold">{reviewing ? (playing ? "Playing replay" : "Replay paused") : replay ? "Recorded investigation" : active ? "Live agent view" : "Latest agent view"}</span>
          {reviewing && active && !replay && <span className="text-xs text-muted-foreground">Agent continues live</span>}
        </div>
        {reviewing && <Button size="sm" variant="secondary" onClick={onLive}><Radio /> {returnLabel}</Button>}
      </div>
      <div className="relative overflow-hidden rounded-md border-2 border-foreground/80 bg-black">
        <div className="relative aspect-[16/10] w-full bg-zinc-950">
          {visible >= 0 ? (
            <>
              <AnimatePresence initial={false}>
                <motion.img
                  key={visible}
                  src={api.frameUrl(runId, visible)}
                  alt={`Agent screen, step ${visible + 1}`}
                  className="absolute inset-0 size-full object-contain"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.35 }}
                />
              </AnimatePresence>
              <AnimatePresence>
                {pointer?.point && (
                  <motion.div
                    key={`${visible}-${pointer.action.index}`}
                    className="pointer-events-none absolute z-10"
                    style={{ left: `${pointer.point.x * 100}%`, top: `${pointer.point.y * 100}%` }}
                    initial={{ opacity: 0, scale: 0.6 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ type: "spring", stiffness: 300, damping: 22 }}
                  >
                    <span className="absolute -top-7 -left-7 size-14 animate-ping rounded-full bg-hazard/40" />
                    <span className="absolute -top-4 -left-4 size-8 rounded-full border-[3px] border-white bg-hazard/70 shadow-lg" />
                    {typeof pointer.action.args.element === "string" && (
                      <span className="absolute top-5 left-5 max-w-80 rounded-sm bg-zinc-950/85 px-3 py-1.5 text-sm leading-snug font-medium whitespace-nowrap text-white shadow-lg ring-1 ring-white/10 backdrop-blur">
                        {pointer.action.args.element}
                      </span>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          ) : (
            <div className="absolute inset-0 grid place-items-center">
              <div role="status" className="flex flex-col items-center gap-3 text-zinc-400">
                {active && <Spinner className="size-10 text-hazard" />}
                <span className="text-sm">{active ? "Opening the lab…" : "No screen recorded"}</span>
              </div>
            </div>
          )}

          <div className="pointer-events-none absolute top-3 left-3 z-20 flex items-center gap-1.5 text-xs font-medium">
            {(replay || reviewing) && (
              <span className="inline-flex items-center gap-1 rounded-sm bg-black/70 px-2 py-1 text-zinc-100 backdrop-blur">
                <MonitorPlay className="size-3.5" /> Replay
              </span>
            )}
            {active && following && !replay && (
              <span className="inline-flex items-center gap-1.5 rounded-sm bg-black/70 px-2 py-1 text-zinc-100 backdrop-blur">
                <span className="size-1.5 animate-pulse rounded-full bg-red-500" /> Live
              </span>
            )}
          </div>
          {frames.length > 0 && (
            <span className="pointer-events-none absolute top-3 right-3 z-20 rounded-sm bg-black/70 px-2 py-1 font-mono text-xs text-zinc-300 tabular-nums backdrop-blur">
              {shown + 1}/{frames.length}
            </span>
          )}

          {lastAction && (
            <div className="absolute inset-x-0 bottom-0 z-20 flex items-center gap-2 bg-gradient-to-t from-black/85 to-transparent px-4 pt-8 pb-3 text-sm font-semibold text-hazard">
              {(() => {
                const Icon = actionStyle(lastAction.tool).icon
                return <Icon className="size-4 shrink-0" />
              })()}
              <span className="truncate">{describe(lastAction)}</span>
            </div>
          )}

          {frames.length > 1 && (
            <>
              <button
                type="button"
                aria-label="Previous screen"
                disabled={shown <= 0}
                onClick={() => onPin(Math.max(0, shown - 1))}
                className="absolute top-1/2 left-3 z-30 grid size-9 -translate-y-1/2 place-items-center rounded-full bg-black/50 text-white opacity-0 ring-1 ring-white/15 backdrop-blur transition group-hover:opacity-100 hover:bg-black/70 focus-visible:opacity-100 disabled:hidden [div:hover>&]:opacity-100"
              >
                <ChevronLeft className="size-5" />
              </button>
              <button
                type="button"
                aria-label="Next screen"
                disabled={shown >= latest}
                onClick={() => onPin(Math.min(latest, shown + 1))}
                className="absolute top-1/2 right-3 z-30 grid size-9 -translate-y-1/2 place-items-center rounded-full bg-black/50 text-white opacity-0 ring-1 ring-white/15 backdrop-blur transition hover:bg-black/70 focus-visible:opacity-100 disabled:hidden [div:hover>&]:opacity-100"
              >
                <ChevronRight className="size-5" />
              </button>
            </>
          )}
        </div>
      </div>

      {frames.length > 1 && <Scrubber frames={frames} shown={shown} onPin={onPin} />}
    </div>
  )
}

function Scrubber({
  frames,
  shown,
  onPin,
}: {
  frames: Frame[]
  shown: number
  onPin: (index: number | null) => void
}) {
  const last = frames.length - 1
  return (
    <div className="flex items-center gap-3">
      <label htmlFor="scrubber" className="sr-only">
        Screen
      </label>
      <input
        id="scrubber"
        type="range"
        min={0}
        max={Math.max(0, last)}
        value={Math.max(0, shown)}
        onChange={(event) => {
          const index = Number(event.target.value)
          onPin(index)
        }}
        className="h-1.5 flex-1 cursor-pointer accent-[var(--crystal)]"
      />
      <span className="shrink-0 font-mono text-xs text-muted-foreground">{shown + 1} / {frames.length}</span>
    </div>
  )
}
