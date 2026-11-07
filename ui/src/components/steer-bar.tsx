import { useState } from "react"
import { CornerDownLeft, Loader2, MessageSquareWarning } from "lucide-react"
import { Button } from "@/components/ui/button"

export function SteerBar({ enabled, busy, onSend }: { enabled: boolean; busy: boolean; onSend: (text: string) => Promise<boolean> }) {
  const [text, setText] = useState("")
  const send = async () => {
    if (!enabled || busy || !text.trim()) return
    if (await onSend(text)) setText("")
  }
  return (
    <form
      className="flex items-center gap-2 rounded-2xl border border-border/70 bg-card/70 p-1.5 pl-3 backdrop-blur focus-within:border-brand/50"
      onSubmit={(event) => {
        event.preventDefault()
        void send()
      }}
    >
      <MessageSquareWarning className="size-4 shrink-0 text-muted-foreground" />
      <label htmlFor="steer" className="sr-only">
        Correction for Jesse
      </label>
      <input
        id="steer"
        value={text}
        disabled={!enabled}
        onChange={(event) => setText(event.target.value)}
        maxLength={4000}
        placeholder={enabled ? "Correct or redirect Jesse, e.g. “check the last reading's settings”" : "Corrections open while the simulator session is live"}
        className="min-w-0 flex-1 bg-transparent py-1.5 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
      />
      <Button type="submit" size="sm" variant="secondary" disabled={!enabled || busy || !text.trim()}>
        {busy ? <Loader2 className="animate-spin" /> : <CornerDownLeft />} Send
      </Button>
    </form>
  )
}
