import { useState, type ReactNode } from "react"
import { motion } from "motion/react"
import { ArrowRight, FlaskConical, Globe, Loader2, Monitor } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Logo } from "@/components/logo"
import type { ResearchContext } from "@/lib/api"

export function Launcher({
  busy,
  onStart,
  mic,
  contexts,
}: {
  busy: boolean
  onStart: (question: string) => Promise<boolean>
  mic: ReactNode
  contexts: ResearchContext[]
}) {
  const [question, setQuestion] = useState("")
  const suggestions = contexts.flatMap((context) =>
    context.supported_questions.slice(0, contexts.length > 1 ? 1 : 2).map((example) => ({ example, context })),
  )
  const submit = () => {
    if (!busy && question.trim()) void onStart(question)
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center py-10">
      <motion.div initial={{ y: 8 }} animate={{ y: 0 }} transition={{ duration: 0.5 }}>
        <h1>
          <Logo size="lg" />
        </h1>
        <p className="mt-5 text-lg text-muted-foreground">Ask or speak a question. Watch the experiment run.</p>
      </motion.div>

      <form
        className="mt-8 flex flex-col gap-3 rounded-3xl border border-border/80 bg-card/80 p-3 shadow-2xl shadow-brand/10 backdrop-blur-xl focus-within:border-brand/50 focus-within:ring-4 focus-within:ring-brand/10 sm:flex-row sm:items-center"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <label htmlFor="question" className="sr-only">
          Research question
        </label>
        <input
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What do you want to find out?"
          maxLength={4000}
          className="min-w-0 flex-1 bg-transparent px-3 py-2 text-base outline-none placeholder:text-muted-foreground"
          autoFocus
        />
        {mic}
        <Button type="submit" size="lg" className="rounded-2xl" disabled={busy || !question.trim()}>
          {busy ? <Loader2 className="animate-spin" /> : null}
          Start experiment <ArrowRight />
        </Button>
      </form>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {suggestions.map(({ example, context }) => (
          <button
            key={example}
            type="button"
            onClick={() => setQuestion(example)}
            className="group flex items-start gap-3 rounded-2xl border border-border/70 bg-card/60 p-4 text-left backdrop-blur transition hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-xl hover:shadow-brand/10"
          >
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand/10 text-brand">
              <FlaskConical className="size-4.5" />
            </span>
            <span className="flex min-w-0 flex-col gap-1">
              <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                {context.application} · {context.title}
                {context.surfaces.includes("web") && <Globe className="size-3" aria-label="Web" />}
                {context.surfaces.includes("desktop") && <Monitor className="size-3" aria-label="Desktop" />}
              </span>
              <span className="text-sm leading-snug font-medium">{example}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
