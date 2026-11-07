import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import { motion } from "motion/react"
import { CheckCircle2, CircleHelp, ExternalLink, FileText, Globe, Monitor, OctagonAlert } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { Snapshot } from "@/lib/api"

const OUTCOME = {
  supported_conclusion: { label: "Supported conclusion", icon: CheckCircle2, className: "text-success bg-success/10 ring-success/25" },
  inconclusive: { label: "Inconclusive", icon: CircleHelp, className: "text-warning bg-warning/12 ring-warning/25" },
  blocked: { label: "Blocked", icon: OctagonAlert, className: "text-destructive bg-destructive/10 ring-destructive/25" },
} as const

function prettyExperiment(id: string | null) {
  if (!id) return "None"
  if (id.startsWith("chemcollective")) return "ChemCollective coolant"
  if (id.startsWith("netlogo")) return "NetLogo Enzyme Kinetics"
  return id
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[88px_minmax(0,1fr)] gap-3 py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 [overflow-wrap:anywhere]">{children}</dd>
    </div>
  )
}

export function Details({ snapshot, report }: { snapshot: Snapshot | null; report: string | null }) {
  const selection = snapshot?.selection
  const outcome = snapshot && !snapshot.active ? snapshot.outcome : null
  const outcomeStyle = outcome ? OUTCOME[outcome.outcome as keyof typeof OUTCOME] : undefined

  return (
    <motion.div
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="flex min-w-0 flex-col gap-4"
    >
      <Card className="gap-2 border-border/70 bg-card/70 py-4 backdrop-blur">
        <CardHeader className="px-5">
          <CardTitle className="text-sm font-medium text-muted-foreground">Experiment</CardTitle>
        </CardHeader>
        <CardContent className="px-5">
          {selection ? (
            <dl className="divide-y divide-border/60">
              <Field label="Simulator">
                <span className="font-medium">{prettyExperiment(selection.experiment_id)}</span>
              </Field>
              <Field label="Surface">
                {selection.surface ? (
                  <Badge variant="secondary" className="gap-1">
                    {selection.surface === "web" ? <Globe className="size-3" /> : <Monitor className="size-3" />}
                    {selection.surface === "web" ? "Hosted browser" : "This Mac"}
                  </Badge>
                ) : (
                  "-"
                )}
              </Field>
              {selection.maximum_trials != null && <Field label="Trial limit">{selection.maximum_trials}</Field>}
              <Field label="Why">
                <span className="text-muted-foreground">{selection.reason}</span>
              </Field>
            </dl>
          ) : (
            <div className="space-y-2 py-1">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <p className="pt-1 text-xs text-muted-foreground">Matching your question to an approved simulator…</p>
            </div>
          )}
        </CardContent>
      </Card>

      {outcome && (
        <Card className="gap-2 border-border/70 bg-card/70 py-4 backdrop-blur">
          <CardHeader className="px-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">Outcome</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 px-5">
            {outcomeStyle && (
              <span
                className={cn(
                  "inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium ring-1 ring-inset",
                  outcomeStyle.className,
                )}
              >
                <outcomeStyle.icon className="size-4" /> {outcomeStyle.label}
              </span>
            )}
            {outcome.reason && <p className="text-sm text-muted-foreground">{outcome.reason}</p>}
          </CardContent>
        </Card>
      )}

      {report && snapshot?.report_url && (
        <Card className="min-h-0 gap-3 border-border/70 bg-card/70 py-4 backdrop-blur">
          <CardHeader className="flex flex-row items-center justify-between px-5">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <FileText className="size-4" /> Report
            </CardTitle>
            <a
              href={snapshot.report_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-brand hover:underline"
            >
              Markdown <ExternalLink className="size-3" />
            </a>
          </CardHeader>
          <CardContent className="px-5">
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
          </CardContent>
        </Card>
      )}
    </motion.div>
  )
}
