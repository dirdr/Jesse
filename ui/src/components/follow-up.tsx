import { useState } from "react"
import { FlaskConical } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Spinner } from "@/components/ui/spinner"
import type { Snapshot } from "@/lib/api"

export function FollowUp({ snapshot, onStart }: {
  snapshot: Snapshot
  onStart: (question: string) => Promise<boolean>
}) {
  const [editing, setEditing] = useState(false)
  const question = snapshot.selection?.question
    ?? snapshot.events.find((event) => event.kind === "question" && event.author === "researcher")?.text
    ?? "Repeat the previous investigation"
  const [prompt, setPrompt] = useState(() => [
    `Investigate again: ${question.slice(0, 2200)}`,
    `Follow-up to investigation ${snapshot.run_id}. Its outcome was inconclusive.`,
    `Evidence gap to resolve: ${(snapshot.outcome?.reason ?? "The evidence did not support a conclusion.").slice(0, 800)}`,
    "Propose a focused plan to resolve this gap using the research notes and approved tools. Collect fresh measurements with units, keep comparison conditions fixed, and repeat measurements to check consistency. Record and explain conflicting readings rather than replacing them in the final narrative. Analyze the recorded data before concluding. The earlier run is context, not verified evidence for this experiment.",
  ].join("\n\n"))
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState(false)

  async function start() {
    if (starting || !prompt.trim()) return
    setStarting(true)
    setError(false)
    try {
      if (!await onStart(prompt.trim())) setError(true)
    } catch {
      setError(true)
    } finally {
      setStarting(false)
    }
  }

  return (
    <section className="mb-5 rounded-md border border-warning/30 bg-warning/5 p-4">
      <h3 className="text-sm font-semibold">What would you like to try next?</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        This result is inconclusive. Shall we run a new experiment to resolve the missing or conflicting evidence?
      </p>
      {!editing ? (
        <Button className="mt-3" size="sm" variant="outline" onClick={() => setEditing(true)}>
          <FlaskConical /> Review proposed experiment
        </Button>
      ) : (
        <form className="mt-3 space-y-3" onSubmit={(event) => { event.preventDefault(); void start() }}>
          <label htmlFor="follow-up-prompt" className="block text-xs font-medium">Proposed question — edit before starting</label>
          <Textarea id="follow-up-prompt" value={prompt} maxLength={4000} disabled={starting}
            onChange={(event) => setPrompt(event.target.value)} className="min-h-52" />
          <p className="text-xs text-muted-foreground">
            {snapshot.active ? "Starting this experiment ends the current session. " : ""}
            The original report and measurements stay in your history. A new experiment has its own execution budget.
          </p>
          {error && <p role="alert" className="text-sm text-destructive">Could not start the new experiment. Your proposed question is kept here; you can try again.</p>}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={starting || !prompt.trim()}>
              {starting ? <Spinner /> : <FlaskConical />}
              {starting ? "Preparing new experiment…" : snapshot.active ? "End session & start new experiment" : "Start new experiment"}
            </Button>
            <Button type="button" size="sm" variant="ghost" disabled={starting} onClick={() => setEditing(false)}>Not now</Button>
          </div>
        </form>
      )}
    </section>
  )
}
