import {
  Check,
  CheckCheck,
  Compass,
  Flag,
  FileText,
  FlaskConical,
  Gauge,
  Hourglass,
  Lightbulb,
  type LucideIcon,
  MonitorPlay,
  OctagonAlert,
  RotateCw,
  Search,
  Send,
  Sparkles,
  Square,
  X,
} from "lucide-react"
import type { ConversationEvent, RunStatus } from "@/lib/api"

type Tone = "brand" | "success" | "warning" | "danger" | "muted"

export const TONE_CLASS: Record<Tone, string> = {
  brand: "bg-brand/12 text-brand ring-brand/20",
  success: "bg-success/12 text-success ring-success/20",
  warning: "bg-warning/14 text-warning ring-warning/25",
  danger: "bg-destructive/12 text-destructive ring-destructive/20",
  muted: "bg-muted text-muted-foreground ring-border",
}

export const KINDS: Record<string, { label: string; icon: LucideIcon; tone: Tone }> = {
  planning: { label: "Planning", icon: Search, tone: "muted" },
  selection: { label: "Experiment chosen", icon: Compass, tone: "brand" },
  session: { label: "Lab opening", icon: MonitorPlay, tone: "muted" },
  plan: { label: "Plan", icon: Lightbulb, tone: "brand" },
  measurement: { label: "Measurement", icon: Gauge, tone: "success" },
  finding: { label: "Finding", icon: Sparkles, tone: "success" },
  follow_up: { label: "Follow-up", icon: RotateCw, tone: "warning" },
  blocker: { label: "Blocker", icon: OctagonAlert, tone: "danger" },
  acknowledged: { label: "Acknowledged", icon: Check, tone: "warning" },
  applied: { label: "Applied", icon: CheckCheck, tone: "success" },
  rejected: { label: "Not applied", icon: X, tone: "danger" },
  waiting: { label: "Report ready", icon: Hourglass, tone: "warning" },
  report_ready: { label: "Report ready", icon: FileText, tone: "success" },
  finished: { label: "Session closed", icon: Flag, tone: "muted" },
  delivered: { label: "Delivered", icon: Send, tone: "muted" },
  delivery_unknown: { label: "Not confirmed", icon: OctagonAlert, tone: "danger" },
  stopping: { label: "Stopping", icon: Square, tone: "danger" },
}

export const FALLBACK_KIND = { label: "Update", icon: FlaskConical, tone: "muted" as Tone }

export const STATUS: Record<RunStatus | "idle", { label: string; tone: Tone; live?: boolean }> = {
  idle: { label: "Ready", tone: "muted" },
  planning: { label: "Choosing an experiment", tone: "brand", live: true },
  running: { label: "Experiment running", tone: "brand", live: true },
  waiting: { label: "Session idle", tone: "muted" },
  report_ready: { label: "Report ready", tone: "success" },
  supported_conclusion: { label: "Supported conclusion", tone: "success" },
  inconclusive: { label: "Inconclusive", tone: "warning" },
  blocked: { label: "Blocked", tone: "danger" },
}

const NOTE_KINDS = new Set(["finding", "follow_up", "blocker"])

export function notesOf(events: ConversationEvent[]) {
  return events.filter((event) => event.author !== "researcher" && NOTE_KINDS.has(event.kind))
}
