import { useState } from "react"
import { ChevronDown, FlaskConical, Globe, Monitor, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Logo } from "@/components/logo"
import { cn } from "@/lib/utils"
import type { ResearchNote, RunSummary } from "@/lib/api"

const OUTCOME_DOT: Record<string, string> = {
  supported_conclusion: "bg-success",
  inconclusive: "bg-warning",
  blocked: "bg-destructive",
}

function bucket(iso: string, now: Date) {
  const day = new Date(iso)
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  if (day.getTime() >= start) return "Today"
  if (day.getTime() >= start - 86_400_000) return "Yesterday"
  if (day.getTime() >= start - 6 * 86_400_000) return "Previous 7 days"
  return "Older"
}

function time(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function RunItem({ run, selected, onOpen }: { run: RunSummary; selected: boolean; onOpen: (run: RunSummary) => void }) {
  const Surface = run.surface === "desktop" ? Monitor : Globe
  return (
    <button
      type="button"
      onClick={() => onOpen(run)}
      aria-current={selected ? "page" : undefined}
      className={cn(
        "group flex w-full flex-col gap-1 rounded-sm border-l-2 border-transparent px-3 py-2 text-left transition-colors hover:bg-sidebar-accent",
        selected && "border-brand bg-sidebar-accent",
      )}
    >
      <span className="line-clamp-2 text-sm leading-snug font-medium text-sidebar-foreground">{run.question}</span>
      <span className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
        {run.active ? (
          <span className="relative flex size-2 shrink-0">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-brand opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-brand" />
          </span>
        ) : (
          <span className={cn("size-2 shrink-0 rounded-full", OUTCOME_DOT[run.outcome ?? ""] ?? "bg-muted-foreground/40")} />
        )}
        {run.surface && <Surface className="size-3 shrink-0" />}
        <span className="truncate">{run.title ?? run.context ?? "Selection only"}</span>
        <span className="ml-auto shrink-0 tabular-nums">{time(run.started_at)}</span>
      </span>
    </button>
  )
}

export function SidebarContent({
  runs,
  notes,
  selectedId,
  onOpen,
  onNew,
}: {
  runs: RunSummary[]
  notes: ResearchNote[]
  selectedId: string | null
  onOpen: (run: RunSummary) => void
  onNew: () => void
}) {
  const [showContexts, setShowContexts] = useState(false)
  const now = new Date()
  const groups: [string, RunSummary[]][] = []
  for (const run of runs) {
    const label = bucket(run.started_at, now)
    const last = groups[groups.length - 1]
    if (last && last[0] === label) last[1].push(run)
    else groups.push([label, [run]])
  }
  const scope = `${notes.length} research note${notes.length === 1 ? "" : "s"}`

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 bg-sidebar p-3">
      <div className="flex items-center justify-between px-1 pt-1">
        <button type="button" onClick={onNew} aria-label="Jesse home">
          <Logo />
        </button>
      </div>
      <Button onClick={onNew} className="justify-start bg-hazard font-semibold text-hazard-foreground hover:bg-hazard/85">
        <Plus /> New investigation
      </Button>
      <div className="rounded-sm text-xs text-muted-foreground ring-1 ring-sidebar-border ring-inset">
        <button
          type="button"
          onClick={() => setShowContexts((value) => !value)}
          aria-expanded={showContexts}
          className="flex w-full items-center gap-2 px-3 py-2 text-left hover:text-foreground"
        >
          <FlaskConical className="size-3.5 shrink-0 text-brand" />
          <span className="min-w-0 flex-1 truncate" title={scope}>
            {scope}
          </span>
          <ChevronDown className={cn("size-3.5 shrink-0 transition-transform", showContexts && "rotate-180")} />
        </button>
        {showContexts && (
          <ul className="flex flex-col gap-1 border-t border-sidebar-border px-3 py-2">
            {notes.map((note) => (
              <li key={note.id} className="truncate text-foreground" title={`research/${note.id}.md`}>
                {note.title}
              </li>
            ))}
          </ul>
        )}
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <nav aria-label="Past investigations" className="flex flex-col gap-4 pr-2">
          {groups.length === 0 && <p className="px-3 text-sm text-muted-foreground">Past investigations appear here.</p>}
          {groups.map(([label, items]) => (
            <section key={label} className="flex flex-col gap-0.5">
              <h2 className="px-3 pb-1 text-xs font-medium text-muted-foreground">{label}</h2>
              {items.map((run) => (
                <RunItem key={run.run_id} run={run} selected={run.run_id === selectedId} onOpen={onOpen} />
              ))}
            </section>
          ))}
        </nav>
      </ScrollArea>
    </div>
  )
}
