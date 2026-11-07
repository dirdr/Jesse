import { useEffect, useMemo, useRef } from "react"
import { motion } from "motion/react"
import { CheckCircle2, Circle, FlaskConical, Loader2, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { actionStyle, describe, plain } from "@/lib/actions"
import { KINDS, TONE_CLASS } from "@/lib/kinds"
import type { Action, ConversationEvent, Measurement, PlanGoal } from "@/lib/api"

function clock(iso: string | null | undefined) {
  if (!iso) return ""
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  } catch {
    return ""
  }
}

export function Panel({ title, aside, children, className }: { title: string; aside?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("flex min-h-0 flex-col rounded-2xl border border-border/70 bg-card/70 backdrop-blur", className)}>
      <header className="flex items-center justify-between gap-2 px-4 pt-3.5 pb-2">
        <h2 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  )
}

export function PlanPanel({ plan }: { plan: PlanGoal[] }) {
  if (!plan.length) return null
  const done = plan.filter((goal) => /done|complete/.test(goal.status)).length
  return (
    <Panel
      title="Agent plan"
      aside={
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {done}/{plan.length}
        </span>
      }
    >
      <div className="mx-4 mb-2 h-1 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-brand to-brand-2"
          animate={{ width: `${(done / plan.length) * 100}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
        />
      </div>
      <ol className="flex flex-col gap-1 px-4 pb-3">
        {plan.map((goal, index) => {
          const isDone = /done|complete/.test(goal.status)
          const isRunning = /run|progress|active/.test(goal.status)
          return (
            <li key={index} className="flex items-start gap-2.5 py-1 text-sm">
              {isDone ? (
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />
              ) : isRunning ? (
                <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-brand" />
              ) : (
                <Circle className="mt-0.5 size-4 shrink-0 text-muted-foreground/50" />
              )}
              <span className={cn("leading-snug", isDone ? "text-muted-foreground" : isRunning ? "font-medium" : "text-muted-foreground")}>
                {goal.title}
              </span>
            </li>
          )
        })}
      </ol>
    </Panel>
  )
}

export function MeasurementsPanel({ measurements }: { measurements: Measurement[] }) {
  return (
    <Panel
      title="Measurements"
      aside={<span className="font-mono text-xs text-muted-foreground tabular-nums">{measurements.length}</span>}
    >
      {measurements.length === 0 ? (
        <p className="px-4 pb-4 text-sm text-muted-foreground">Readings appear here as soon as Jesse records them.</p>
      ) : (
        <ul className="flex flex-col gap-2 px-3 pb-3">
          {measurements.map((row) => (
            <motion.li
              key={row.id}
              initial={{ y: 6 }}
              animate={{ y: 0 }}
              className="rounded-xl border border-border/60 bg-background/60 p-3"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono text-xs font-medium">{row.id}</span>
                <span className="font-mono text-[11px] text-muted-foreground">{clock(row.at)}</span>
              </div>
              {row.result && <div className="mt-1 text-lg font-semibold tracking-tight tabular-nums">{row.result}</div>}
              <div className="mt-2 flex flex-wrap gap-1.5">
                {Object.entries(row.fields).map(([key, value]) => (
                  <span key={key} className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                    {key} <span className="text-foreground">{value}</span>
                  </span>
                ))}
              </div>
            </motion.li>
          ))}
        </ul>
      )}
    </Panel>
  )
}

type TimelineItem =
  | { type: "action"; at: string; action: Action }
  | { type: "event"; at: string; event: ConversationEvent }

const SHOWN_EVENTS = new Set(["plan", "finding", "follow_up", "blocker", "acknowledged", "applied", "rejected", "selection", "measurement", "question"])

export function ActivityPanel({
  actions,
  events,
  selectedFrame,
  onSelectFrame,
}: {
  actions: Action[]
  events: ConversationEvent[]
  selectedFrame: number | null
  onSelectFrame: (frame: number) => void
}) {
  const items = useMemo<TimelineItem[]>(() => {
    const list: TimelineItem[] = [
      ...actions.filter((action) => action.tool !== "update_plan").map((action) => ({ type: "action" as const, at: action.at, action })),
      ...events.filter((event) => SHOWN_EVENTS.has(event.kind)).map((event) => ({ type: "event" as const, at: event.at, event })),
    ]
    return list.sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime())
  }, [actions, events])

  const scroller = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const element = scroller.current
    if (element) element.scrollTo({ top: element.scrollHeight, behavior: "smooth" })
  }, [items.length])

  return (
    <Panel title="Activity" className="min-h-[260px] flex-1">
      <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        {items.length === 0 && <p className="px-2 pb-2 text-sm text-muted-foreground">Waiting for the first action…</p>}
        <ol className="relative flex flex-col">
          {items.map((item, index) =>
            item.type === "action" ? (
              <li key={`a${item.action.index}`}>
                <button
                  type="button"
                  disabled={item.action.frame === null}
                  onClick={() => item.action.frame !== null && onSelectFrame(item.action.frame)}
                  className={cn(
                    "group flex w-full items-start gap-2.5 rounded-lg px-2 py-1.5 text-left transition hover:bg-muted/70",
                    selectedFrame !== null && item.action.frame === selectedFrame && "bg-brand/10",
                  )}
                >
                  {(() => {
                    const Icon = actionStyle(item.action.tool).icon
                    return (
                      <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground group-hover:text-foreground">
                        <Icon className="size-3.5" />
                      </span>
                    )
                  })()}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-medium">{describe(item.action)}</span>
                    {item.action.text && <span className="line-clamp-2 text-xs text-muted-foreground">{plain(item.action.text)}</span>}
                  </span>
                  <span className="shrink-0 pt-0.5 font-mono text-[10px] text-muted-foreground tabular-nums">{clock(item.at)}</span>
                </button>
              </li>
            ) : (
              <li key={`e${item.event.id}-${index}`} className="px-1 py-1">
                <EventCard event={item.event} />
              </li>
            ),
          )}
        </ol>
      </div>
    </Panel>
  )
}

function EventCard({ event }: { event: ConversationEvent }) {
  const researcher = event.author === "researcher"
  const kind = KINDS[event.kind]
  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-2 text-[13px] leading-snug",
        researcher ? "border-brand/30 bg-brand/8" : "border-border/70 bg-background/70",
      )}
    >
      <div className="mb-1 flex items-center gap-1.5 text-[11px]">
        {researcher ? <User className="size-3 text-brand" /> : <FlaskConical className="size-3 text-brand" />}
        <span className="font-medium">{researcher ? (event.source === "voice" ? "You (voice)" : "You") : "Jesse"}</span>
        {!researcher && kind && (
          <span className={cn("rounded-full px-1.5 py-px text-[10px] font-medium ring-1 ring-inset", TONE_CLASS[kind.tone])}>{kind.label}</span>
        )}
        <span className="ml-auto font-mono text-[10px] text-muted-foreground">{clock(event.at)}</span>
      </div>
      <p className="whitespace-pre-wrap">{event.text}</p>
    </div>
  )
}
