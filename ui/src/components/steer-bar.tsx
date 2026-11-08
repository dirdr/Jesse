import { useMemo, useRef, useState } from "react"
import { ArrowUp, Compass, CornerDownLeft, History, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Spinner } from "@/components/ui/spinner"
import { describe } from "@/lib/actions"
import { KINDS, TONE_CLASS } from "@/lib/kinds"
import type { Action, ConversationEvent } from "@/lib/api"

const SUGGESTIONS = [
  "Repeat the last trial before concluding",
  "Double-check the units and settings",
  "Explain your last decision",
]

const STATUS_ORDER = ["delivered", "delivery_unknown", "acknowledged", "applied", "rejected"]

function corrections(events: ConversationEvent[]) {
  const status = new Map<string, string>()
  for (const event of events) {
    if (!event.message_id || event.author === "researcher") continue
    const current = status.get(event.message_id)
    if (!current || STATUS_ORDER.indexOf(event.kind) >= STATUS_ORDER.indexOf(current)) status.set(event.message_id, event.kind)
  }
  return events
    .filter((event) => event.author === "researcher" && event.kind === "question" && event.message_id)
    .slice(-2)
    .map((event) => ({ event, status: status.get(event.message_id!) ?? "pending" }))
}

export function SteerBar({
  enabled,
  busy,
  onSend,
  events,
  step,
  onClearStep,
}: {
  enabled: boolean
  busy: boolean
  onSend: (text: string) => Promise<boolean>
  events: ConversationEvent[]
  step: Action | null
  onClearStep: () => void
}) {
  const [text, setText] = useState("")
  const input = useRef<HTMLTextAreaElement>(null)
  const recent = useMemo(() => corrections(events), [events])
  const ready = enabled && !busy && text.trim().length > 0

  const send = async () => {
    if (!ready) return
    const body = step ? `Regarding step ${step.index + 1} (${describe(step)}): ${text.trim()}` : text.trim()
    if (await onSend(body)) {
      setText("")
      onClearStep()
    }
  }

  return (
    <section
      aria-label="Correct or redirect Jesse"
      className={cn(
        "overflow-hidden rounded-md border-2 bg-card transition-colors",
        enabled ? "border-foreground/70 focus-within:border-hazard" : "border-border",
      )}
    >
      <header className="flex items-center gap-2 border-b border-border bg-muted/40 px-3 py-2">
        <Compass className="size-4 text-brand" />
        <h2 className="text-sm font-semibold">Correct or redirect Jesse</h2>
        <span className="flex-1" />
        <span className={cn("inline-flex items-center gap-1.5 text-[11px] font-medium", enabled ? "text-success" : "text-muted-foreground")}>
          <span className={cn("size-1.5 rounded-full", enabled ? "animate-pulse bg-success" : "bg-muted-foreground/50")} />
          {enabled ? "Session listening" : "Opens when the lab session is live"}
        </span>
      </header>

      {recent.length > 0 && (
        <ul className="flex flex-col gap-1 border-b border-border px-3 py-2">
          {recent.map(({ event, status }) => {
            const kind = KINDS[status]
            return (
              <li key={event.message_id} className="flex items-center gap-2 text-xs">
                <span className="min-w-0 flex-1 truncate text-muted-foreground">“{event.text}”</span>
                <span
                  className={cn(
                    "shrink-0 rounded-full px-1.5 py-px text-[10px] font-medium ring-1 ring-inset",
                    TONE_CLASS[kind?.tone ?? "muted"],
                  )}
                >
                  {kind?.label ?? "Sending"}
                </span>
              </li>
            )
          })}
        </ul>
      )}

      <form
        className="flex flex-col gap-2 p-3"
        onSubmit={(event) => {
          event.preventDefault()
          void send()
        }}
      >
        {step && (
          <div className="flex items-center gap-2 self-start rounded-sm bg-hazard/15 py-1 pr-1 pl-2 text-xs font-medium ring-1 ring-hazard/40">
            <History className="size-3.5" />
            <span className="max-w-72 truncate">
              About step {step.index + 1} · {describe(step)}
            </span>
            <button type="button" onClick={onClearStep} aria-label="Stop referring to this step" className="grid size-5 place-items-center rounded-sm hover:bg-hazard/25">
              <X className="size-3" />
            </button>
          </div>
        )}
        <label htmlFor="steer" className="sr-only">
          Correction for Jesse
        </label>
        <div className="flex items-end gap-2">
          <textarea
            id="steer"
            ref={input}
            rows={1}
            value={text}
            disabled={!enabled}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault()
                void send()
              }
            }}
            maxLength={4000}
            placeholder={
              enabled
                ? step
                  ? "What should Jesse do differently from this step?"
                  : "Tell Jesse what to check, change or repeat…"
                : "Corrections open while the simulator session is live"
            }
            className="field-sizing-content max-h-40 min-h-9 min-w-0 flex-1 resize-none bg-transparent py-1.5 text-sm leading-relaxed outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!ready}
            aria-label="Send correction"
            className="grid size-9 shrink-0 place-items-center rounded-md bg-hazard text-hazard-foreground shadow-sm transition hover:brightness-95 disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none"
          >
            {busy ? <Spinner /> : <ArrowUp className="size-4" />}
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              disabled={!enabled}
              onClick={() => {
                setText(suggestion)
                input.current?.focus()
              }}
              className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground transition hover:border-foreground/40 hover:text-foreground disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
          <span className="flex-1" />
          <span className="hidden items-center gap-1 text-[11px] text-muted-foreground sm:inline-flex">
            <CornerDownLeft className="size-3" /> send · Shift <CornerDownLeft className="size-3" /> new line
          </span>
        </div>
      </form>
    </section>
  )
}
