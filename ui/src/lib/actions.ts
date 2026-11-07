import {
  Command,
  Database,
  Globe,
  Keyboard,
  ListChecks,
  type LucideIcon,
  Megaphone,
  MessageSquare,
  MousePointerClick,
  MoveVertical,
  Sigma,
  Terminal,
  Timer,
  ZoomIn,
  Zap,
} from "lucide-react"
import type { Action, Frame } from "@/lib/api"

interface ActionStyle {
  icon: LucideIcon
  verb: string
}

const BY_PREFIX: [string, ActionStyle][] = [
  ["click", { icon: MousePointerClick, verb: "Click" }],
  ["double_click", { icon: MousePointerClick, verb: "Double-click" }],
  ["write", { icon: Keyboard, verb: "Type" }],
  ["type", { icon: Keyboard, verb: "Type" }],
  ["hotkey", { icon: Command, verb: "Shortcut" }],
  ["press", { icon: Command, verb: "Key" }],
  ["zoom", { icon: ZoomIn, verb: "Inspect" }],
  ["wait", { icon: Timer, verb: "Wait" }],
  ["scroll", { icon: MoveVertical, verb: "Scroll" }],
  ["drag", { icon: MousePointerClick, verb: "Drag" }],
  ["navigate", { icon: Globe, verb: "Open page" }],
  ["goto", { icon: Globe, verb: "Open page" }],
  ["run_command", { icon: Terminal, verb: "Command" }],
  ["record", { icon: Database, verb: "Record" }],
  ["analyze", { icon: Sigma, verb: "Analyze" }],
  ["publish_update", { icon: Megaphone, verb: "Update" }],
  ["acknowledge", { icon: MessageSquare, verb: "Reply" }],
  ["update_plan", { icon: ListChecks, verb: "Plan" }],
  ["message", { icon: MessageSquare, verb: "Note" }],
]

export function actionStyle(tool: string): ActionStyle {
  return BY_PREFIX.find(([prefix]) => tool.startsWith(prefix))?.[1] ?? { icon: Zap, verb: tool.replace(/_/g, " ") }
}

/** One-line description of what the agent did. */
export function describe(action: Action): string {
  const { args } = action
  const style = actionStyle(action.tool)
  if (typeof args.element === "string") return `${style.verb} · ${args.element}`
  if (typeof args.content === "string" && action.tool.startsWith("write")) return `${style.verb} “${args.content}”`
  if (Array.isArray(args.keys)) return `${style.verb} ${(args.keys as string[]).join(" + ")}`
  if (typeof args.seconds === "number") return `${style.verb} ${args.seconds}s`
  if (typeof args.url === "string") return `${style.verb} · ${args.url}`
  if (action.tool.startsWith("record") && args.trial_id) return `${style.verb} measurement · ${args.trial_id}`
  return style.verb
}

/** Pointer position as a fraction of the screenshot, when the action targets a point. */
export function pointOf(action: Action, frame: Frame | undefined): { x: number; y: number } | null {
  const { x, y } = action.args
  if (typeof x !== "number" || typeof y !== "number") return null
  if (x <= 1 && y <= 1) return { x, y }
  const [width, height] = frame?.viewport ?? [0, 0]
  if (!width || !height) return null
  return { x: x / width, y: y / height }
}
