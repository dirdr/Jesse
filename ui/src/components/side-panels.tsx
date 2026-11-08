import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import type { Measurement, PlanGoal } from "@/lib/api"


export function Panel({ title, aside, children, className }: { title: string; aside?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("flex min-h-0 flex-col rounded-md border border-border bg-card", className)}>
      <header className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5">
        <h2 className="text-sm font-semibold">{title}</h2>
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
      <div className="mx-4 mt-3 mb-2 h-1.5 overflow-hidden rounded-sm bg-muted">
        <motion.div
          className="h-full bg-crystal"
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
              <span
                className={cn(
                  "grid h-6 w-7 shrink-0 place-items-center rounded-sm border font-mono text-[11px] font-semibold tabular-nums",
                  isDone ? "border-brand bg-brand text-primary-foreground dark:text-background" : isRunning ? "border-crystal bg-crystal/15 text-crystal" : "border-border text-muted-foreground",
                )}
                aria-hidden
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className={cn("pt-0.5 leading-snug", isDone ? "text-muted-foreground" : isRunning ? "font-medium" : "text-muted-foreground")}>
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
  const varied = new Set(
    Object.keys(measurements[0]?.fields ?? {}).filter(
      (key) => new Set(measurements.map((row) => row.fields[key])).size > 1,
    ),
  )
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
              className="rounded-sm border border-border bg-background/70 p-3"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono text-xs font-medium">{row.id}</span>
              </div>
              {row.result && <div className="mt-1 font-mono text-lg font-semibold text-crystal tabular-nums">{row.result}</div>}
              <div className="mt-2 flex flex-wrap gap-1.5">
                {Object.entries(row.fields).filter(([key]) => varied.has(key)).map(([key, value]) => (
                  <span key={key} className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
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
