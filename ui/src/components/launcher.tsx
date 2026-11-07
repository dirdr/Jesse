import { useState, type ReactNode } from "react"
import { motion } from "motion/react"
import { FlaskConical } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Logo } from "@/components/logo"

export function Launcher({
  busy,
  onStart,
  mic,
}: {
  busy: boolean
  onStart: (question: string) => Promise<boolean>
  mic: ReactNode
}) {
  const [question, setQuestion] = useState("")
  const submit = () => {
    if (!busy && question.trim()) void onStart(question)
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center py-10">
      <motion.h1 initial={{ y: 12 }} animate={{ y: 0 }} transition={{ duration: 0.5, ease: "easeOut" }}>
        <Logo size="lg" />
      </motion.h1>

      <form
        className="mt-10 flex flex-col gap-2 rounded-md border-2 border-foreground/80 bg-card p-2 shadow-[6px_6px_0_0_var(--brand)] transition-shadow focus-within:shadow-[6px_6px_0_0_var(--hazard)] sm:flex-row sm:items-center"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <label htmlFor="question" className="sr-only">
          Research question
        </label>
        <FlaskConical className="ml-2 hidden size-5 shrink-0 text-brand sm:block" aria-hidden />
        <input
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What do you want to find out?"
          maxLength={4000}
          className="min-w-0 flex-1 bg-transparent px-2 py-2.5 text-lg outline-none placeholder:text-muted-foreground"
          autoFocus
        />
        <div className="flex items-center gap-2">
          {mic}
          <Button
            type="submit"
            size="lg"
            className="flex-1 bg-hazard font-semibold text-hazard-foreground hover:bg-hazard/85 disabled:opacity-100 disabled:bg-hazard/35 disabled:text-hazard-foreground/70 sm:flex-none dark:disabled:text-foreground/60"
            disabled={busy || !question.trim()}
          >
            {busy && <Spinner />}
            Start experiment
          </Button>
        </div>
      </form>
    </div>
  )
}
