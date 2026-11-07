import { useEffect, useMemo, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { ChevronLeft, ChevronRight, MonitorPlay, Radio } from "lucide-react"
import { Button } from "@/components/ui/button"
import { actionStyle, describe, plain, pointOf } from "@/lib/actions"
import { api, type Action, type Frame } from "@/lib/api"


interface LiveScreenProps {
  runId: string
  frames: Frame[]
  actions: Action[]
  active: boolean
  replay: boolean
  pinned: number | null
  onPin: (index: number | null) => void
}

export function LiveScreen({ runId, frames, actions, active, replay, pinned, onPin }: LiveScreenProps) {
  const latest = frames.length - 1
  const shown = pinned ?? latest
  const following = pinned === null
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

  const frameActions = useMemo(() => actions.filter((action) => action.frame === visible), [actions, visible])
  const pointer = frameActions.map((action) => ({ action, point: pointOf(action, frames[visible]) })).find((item) => item.point)
  const caption = [...frameActions].reverse().find((action) => action.text)?.text
  const lastAction = frameActions.at(-1)

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <div className="relative overflow-hidden rounded-2xl border border-border/70 bg-black shadow-2xl shadow-black/20 ring-1 ring-white/5">
        <div className="flex items-center justify-between gap-3 border-b border-white/10 bg-zinc-950/90 px-4 py-2 text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            {replay ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2 py-0.5 font-medium text-zinc-200">
                <MonitorPlay className="size-3.5" /> Replay
              </span>
            ) : active && following ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/15 px-2 py-0.5 font-medium text-red-400">
                <span className="relative flex size-2">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-red-400 opacity-70" />
                  <span className="relative inline-flex size-2 rounded-full bg-red-500" />
                </span>
                Live
              </span>
            ) : (
              <span className="rounded-full bg-white/10 px-2 py-0.5 font-medium text-zinc-300">Paused view</span>
            )}
          </div>
          <div className="flex items-center gap-3 font-mono tabular-nums">
            {frames.length > 0 && (
              <span>
                {shown + 1}/{frames.length}
              </span>
            )}
          </div>
        </div>

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
                    <span className="absolute -top-5 -left-5 size-10 animate-ping rounded-full bg-brand/40" />
                    <span className="absolute -top-3 -left-3 size-6 rounded-full border-2 border-white bg-brand/70 shadow-lg shadow-brand/50" />
                    {typeof pointer.action.args.element === "string" && (
                      <span className="absolute top-4 left-4 max-w-56 rounded-md bg-zinc-950/85 px-2 py-1 text-[11px] leading-tight font-medium whitespace-nowrap text-white shadow-lg ring-1 ring-white/10 backdrop-blur">
                        {pointer.action.args.element}
                      </span>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          ) : (
            <div className="absolute inset-0 grid place-items-center">
              <div className="flex flex-col items-center gap-3 text-zinc-400">
                <div className="size-10 animate-spin rounded-full border-2 border-zinc-700 border-t-brand" />
                <span className="text-sm">{active ? "Opening the laboratory…" : "No screen was recorded for this run."}</span>
              </div>
            </div>
          )}

          {(caption || lastAction) && (
            <div className="absolute inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black/90 via-black/60 to-transparent px-5 pt-10 pb-4">
              {lastAction && (
                <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium tracking-wide text-brand-2 uppercase">
                  {(() => {
                    const Icon = actionStyle(lastAction.tool).icon
                    return <Icon className="size-3.5" />
                  })()}
                  {describe(lastAction)}
                </div>
              )}
              {caption && <p className="truncate text-sm text-white/90">{plain(caption)}</p>}
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
                onClick={() => onPin(shown + 1 >= latest ? null : shown + 1)}
                className="absolute top-1/2 right-3 z-30 grid size-9 -translate-y-1/2 place-items-center rounded-full bg-black/50 text-white opacity-0 ring-1 ring-white/15 backdrop-blur transition hover:bg-black/70 focus-visible:opacity-100 disabled:hidden [div:hover>&]:opacity-100"
              >
                <ChevronRight className="size-5" />
              </button>
            </>
          )}
        </div>
      </div>

      {frames.length > 1 && <Scrubber frames={frames} shown={shown} following={following} onPin={onPin} />}
    </div>
  )
}

function Scrubber({
  frames,
  shown,
  following,
  onPin,
}: {
  frames: Frame[]
  shown: number
  following: boolean
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
          onPin(index >= last ? null : index)
        }}
        className="h-1.5 flex-1 cursor-pointer accent-[var(--brand)]"
      />
      {!following && (
        <Button size="sm" variant="secondary" onClick={() => onPin(null)} className="shrink-0">
          <Radio /> Latest
        </Button>
      )}
    </div>
  )
}
