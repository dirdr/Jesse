import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import { KINDS, TONE_CLASS } from "@/lib/kinds"
import type { ConversationEvent, Measurement, PlanGoal } from "@/lib/api"

export function Panel({ title, aside, children, className }: { title: string; aside?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("flex min-h-0 flex-col rounded-md border border-border bg-card", className)}>
      <header className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
        <h2 className="text-sm font-semibold">{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  )
}

const isDone = (goal: PlanGoal) => /done|complete/.test(goal.status)

export function PlanStrip({ plan }: { plan: PlanGoal[] }) {
  if (!plan.length) return null
  const done = plan.filter(isDone).length
  const current = plan.find((goal) => /run|progress|active/.test(goal.status)) ?? plan.find((goal) => !isDone(goal))
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2">
      <div className="flex items-baseline gap-2 text-sm">
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {done}/{plan.length}
        </span>
        <span className="min-w-0 flex-1 truncate font-medium" title={current?.title}>
          {current ? current.title : "Plan complete"}
        </span>
      </div>
      <div className="mt-2 flex gap-0.5" aria-hidden>
        {plan.map((goal, index) => (
          <span
            key={index}
            title={goal.title}
            className={cn("h-1 flex-1 rounded-full", isDone(goal) ? "bg-brand" : goal === current ? "bg-crystal" : "bg-muted")}
          />
        ))}
      </div>
    </div>
  )
}

export function Notebook({ measurements, notes }: { measurements: Measurement[]; notes: ConversationEvent[] }) {
  const keys = Object.keys(measurements[0]?.fields ?? {})
  const varied = measurements.length < 2 ? keys : keys.filter((key) => new Set(measurements.map((row) => row.fields[key])).size > 1)
  return (
    <Panel
      title="Lab notebook"
      aside={
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {measurements.length} {measurements.length === 1 ? "reading" : "readings"}
        </span>
      }
    >
      {measurements.length === 0 ? (
        <p className="px-3 py-3 text-sm text-muted-foreground">No readings yet</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs tabular-nums">
            <thead className="text-muted-foreground">
              <tr className="border-b border-border">
                <th scope="col" className="px-3 py-1.5 font-medium">Trial</th>
                {varied.map((key) => (
                  <th key={key} scope="col" className="px-2 py-1.5 font-medium">{key}</th>
                ))}
                <th scope="col" className="px-3 py-1.5 text-right font-medium">Result</th>
              </tr>
            </thead>
            <tbody>
              {measurements.map((row) => (
                <motion.tr
                  key={row.id}
                  initial={{ backgroundColor: "rgba(242, 194, 0, 0.35)" }}
                  animate={{ backgroundColor: "rgba(242, 194, 0, 0)" }}
                  transition={{ duration: 1.6 }}
                  className="border-b border-border/60 last:border-0"
                >
                  <td className="px-3 py-1.5 font-medium">{row.id}</td>
                  {varied.map((key) => (
                    <td key={key} className="px-2 py-1.5 text-muted-foreground">{row.fields[key]}</td>
                  ))}
                  <td className="px-3 py-1.5 text-right text-sm font-semibold text-crystal">{row.result ?? "—"}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {notes.length > 0 && (
        <ul className="flex flex-col gap-1.5 border-t border-border px-3 py-2.5">
          {notes.map((note) => {
            const kind = KINDS[note.kind]
            return (
              <li key={note.id} className="flex items-start gap-2 text-[13px] leading-snug">
                {kind && (
                  <span className={cn("mt-px shrink-0 rounded-sm px-1.5 py-px text-[10px] font-semibold ring-1 ring-inset", TONE_CLASS[kind.tone])}>
                    {kind.label}
                  </span>
                )}
                <span className="line-clamp-3">{note.text}</span>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}
