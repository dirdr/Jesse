import { useEffect, useMemo, useRef } from "react"
import { FlaskConical, Pause, Play, Radio, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { actionStyle, describe, plain } from "@/lib/actions"
import { KINDS, TONE_CLASS } from "@/lib/kinds"
import type { Action, ConversationEvent } from "@/lib/api"
import { Panel } from "@/components/side-panels"

type Item =
  | { type: "action"; at: number; action: Action; reasoning: string | null }
  | { type: "event"; at: number; event: ConversationEvent }

const SHOWN_EVENTS = new Set(["finding", "follow_up", "blocker", "question", "applied", "rejected"])

function time(at: string | null | undefined) {
  const value = at ? Date.parse(at) : NaN
  return Number.isNaN(value) ? 0 : value
}

function elapsed(ms: number) {
  const seconds = Math.max(0, Math.round(ms / 1000))
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`
}

export function DecisionsPanel({
  actions,
  events,
  focus,
  playing,
  onSelect,
  onTogglePlay,
  onLive,
  live,
}: {
  actions: Action[]
  events: ConversationEvent[]
  focus: number | null
  playing: boolean
  onSelect: (index: number) => void
  onTogglePlay: () => void
  onLive: () => void
  live: boolean
}) {
  const items = useMemo<Item[]>(() => {
    const list: Item[] = actions.map((action, index) => {
      const previous = actions[index - 1]
      const repeated = previous && previous.text === action.text && previous.at === action.at
      return { type: "action", at: time(action.at), action, reasoning: action.text && !repeated ? plain(action.text) : null }
    })
    for (const event of events) {
      if (SHOWN_EVENTS.has(event.kind)) list.push({ type: "event", at: time(event.at), event })
    }
    return list.sort((a, b) => a.at - b.at)
  }, [actions, events])

  const start = items.find((item) => item.at > 0)?.at ?? 0
  const cutoff = focus !== null ? time(actions[focus]?.at) : null
  const scroller = useRef<HTMLDivElement>(null)
  const selected = useRef<HTMLLIElement>(null)

  useEffect(() => {
    if (focus !== null) {
      selected.current?.scrollIntoView({ block: "nearest", behavior: "smooth" })
      return
    }
    const element = scroller.current
    if (element) element.scrollTo({ top: element.scrollHeight, behavior: "smooth" })
  }, [focus, items.length])

  return (
    <Panel
      title="Agent decisions"
      className="max-h-[560px] min-h-[260px] flex-1 xl:max-h-none"
      aside={
        <div className="flex items-center gap-1">
          <span className="mr-1 font-mono text-xs text-muted-foreground tabular-nums">
            {focus !== null ? `${focus + 1}/` : ""}
            {actions.length}
          </span>
          <button
            type="button"
            onClick={onTogglePlay}
            disabled={actions.length === 0}
            aria-label={playing ? "Pause replay" : focus === null ? "Replay from the start" : "Resume replay"}
            className="grid size-7 place-items-center rounded-sm text-muted-foreground transition hover:bg-muted hover:text-foreground disabled:opacity-40"
          >
            {playing ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
          </button>
          {focus !== null && (
            <button
              type="button"
              onClick={onLive}
              className="inline-flex h-7 items-center gap-1 rounded-sm px-2 text-xs font-medium text-brand transition hover:bg-brand/10"
            >
              <Radio className="size-3.5" /> {live ? "Live" : "Latest"}
            </button>
          )}
        </div>
      }
    >
      <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        {items.length === 0 && <p className="px-2 py-1 text-sm text-muted-foreground">Each decision H makes in the lab appears here.</p>}
        <ol className="relative flex flex-col">
          {items.map((item, position) => {
            const future = cutoff !== null && item.at > cutoff
            if (item.type === "event") {
              return (
                <li key={`e${item.event.id}-${position}`} className={cn("px-1 py-1 transition-opacity", future && "opacity-35")}>
                  <EventNote event={item.event} />
                </li>
              )
            }
            const { action, reasoning } = item
            const isFocus = focus === action.index
            const Icon = actionStyle(action.tool).icon
            return (
              <li key={`a${action.index}`} ref={isFocus ? selected : undefined} className={cn("transition-opacity", future && "opacity-35")}>
                <button
                  type="button"
                  onClick={() => onSelect(action.index)}
                  aria-current={isFocus ? "step" : undefined}
                  className={cn(
                    "group relative flex w-full items-start gap-2.5 rounded-sm py-1.5 pr-2 pl-2 text-left transition hover:bg-muted/70",
                    isFocus && "bg-hazard/12 ring-1 ring-hazard/50 hover:bg-hazard/15",
                  )}
                >
                  <span className="flex shrink-0 flex-col items-center gap-1 pt-0.5">
                    <span
                      className={cn(
                        "grid size-6 place-items-center rounded-md bg-muted text-muted-foreground group-hover:text-foreground",
                        isFocus && "bg-hazard text-hazard-foreground group-hover:text-hazard-foreground",
                      )}
                    >
                      <Icon className="size-3.5" />
                    </span>
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline gap-2">
                      <span className="min-w-0 flex-1 truncate text-[13px] font-medium">{describe(action)}</span>
                      <span className="shrink-0 font-mono text-[10px] text-muted-foreground tabular-nums">
                        {start ? elapsed(item.at - start) : `#${action.index + 1}`}
                      </span>
                    </span>
                    {reasoning && (
                      <span className={cn("mt-0.5 block text-xs leading-snug text-muted-foreground", !isFocus && "line-clamp-2")}>
                        {reasoning}
                      </span>
                    )}
                  </span>
                </button>
              </li>
            )
          })}
        </ol>
      </div>
    </Panel>
  )
}

function EventNote({ event }: { event: ConversationEvent }) {
  const researcher = event.author === "researcher"
  const kind = KINDS[event.kind]
  return (
    <div
      className={cn(
        "rounded-sm border px-3 py-2 text-[13px] leading-snug",
        researcher ? "border-brand/30 bg-brand/8" : "border-border/70 bg-background/70",
      )}
    >
      <div className="mb-1 flex items-center gap-1.5 text-[11px]">
        {researcher ? <User className="size-3 text-brand" /> : <FlaskConical className="size-3 text-brand" />}
        <span className="font-medium">{researcher ? (event.source === "voice" ? "You (voice)" : "You") : "Jesse"}</span>
        {!researcher && kind && (
          <span className={cn("rounded-full px-1.5 py-px text-[10px] font-medium ring-1 ring-inset", TONE_CLASS[kind.tone])}>{kind.label}</span>
        )}
      </div>
      <p className="line-clamp-4 whitespace-pre-wrap">{event.text}</p>
    </div>
  )
}
