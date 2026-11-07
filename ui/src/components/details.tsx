import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import { CheckCircle2, CircleHelp, ExternalLink, Globe, Monitor, OctagonAlert } from "lucide-react"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"
import type { Snapshot } from "@/lib/api"

const OUTCOME = {
  supported_conclusion: { label: "Supported conclusion", icon: CheckCircle2, className: "text-success bg-success/10 ring-success/25" },
  inconclusive: { label: "Inconclusive", icon: CircleHelp, className: "text-warning bg-warning/12 ring-warning/25" },
  blocked: { label: "Blocked", icon: OctagonAlert, className: "text-destructive bg-destructive/10 ring-destructive/25" },
} as const

export function experimentName(id: string | null | undefined) {
  if (!id) return null
  if (id.startsWith("chemcollective")) return "ChemCollective coolant"
  if (id.startsWith("netlogo")) return "NetLogo Enzyme Kinetics"
  return id
}

export function OutcomeBadge({ outcome }: { outcome: string }) {
  const style = OUTCOME[outcome as keyof typeof OUTCOME]
  if (!style) return null
  return (
    <span className={cn("inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium ring-1 ring-inset", style.className)}>
      <style.icon className="size-4" /> {style.label}
    </span>
  )
}

export function ReportSheet({
  open,
  onOpenChange,
  snapshot,
  report,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  snapshot: Snapshot | null
  report: string | null
}) {
  const selection = snapshot?.selection
  const outcome = snapshot && !snapshot.active ? snapshot.outcome : null
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-2xl">
        <SheetHeader className="border-b border-border/70 pb-4">
          <SheetTitle>Investigation report</SheetTitle>
          <SheetDescription>{selection?.question ?? "Report for this investigation"}</SheetDescription>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            {outcome && <OutcomeBadge outcome={outcome.outcome} />}
            {experimentName(selection?.experiment_id) && (
              <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 font-medium">
                {selection?.surface === "desktop" ? <Monitor className="size-3" /> : <Globe className="size-3" />}
                {experimentName(selection?.experiment_id)}
              </span>
            )}
            {snapshot?.report_url && (
              <a href={snapshot.report_url} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex items-center gap-1 text-brand hover:underline">
                Markdown <ExternalLink className="size-3" />
              </a>
            )}
          </div>
        </SheetHeader>
        <div className="px-4 py-5">
          {outcome?.reason && <p className="mb-5 rounded-xl bg-muted/60 p-3 text-sm text-muted-foreground">{outcome.reason}</p>}
          {report ? (
            <article className="report text-sm leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  a: ({ href, children }) =>
                    href && /^https?:/.test(href) ? (
                      <a href={href} target="_blank" rel="noopener noreferrer" className="text-brand hover:underline">
                        {children}
                      </a>
                    ) : (
                      <span className="text-brand" title={href ? `Run file: ${href}` : undefined}>
                        {children}
                      </span>
                    ),
                }}
              >
                {report}
              </ReactMarkdown>
            </article>
          ) : (
            <p className="text-sm text-muted-foreground">The report appears when Jesse finishes the investigation.</p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
