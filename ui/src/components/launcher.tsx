import { useState } from "react"
import { motion } from "motion/react"
import { ArrowRight, FlaskConical, Loader2, Thermometer } from "lucide-react"
import { Button } from "@/components/ui/button"

const EXPERIMENTS = [
  {
    question: "Can this coolant absorb more heat than the reference coolant?",
    tool: "ChemCollective",
    detail: "Mixing calorimetry against ethylene glycol, 2.200 J/(g·°C)",
    icon: Thermometer,
  },
  {
    question: "Does adding more substrate make an enzyme reaction faster?",
    tool: "NetLogo Enzyme Kinetics",
    detail: "Reaction velocity at different substrate volumes, constants fixed",
    icon: FlaskConical,
  },
]

export function Launcher({ busy, onStart }: { busy: boolean; onStart: (question: string) => Promise<boolean> }) {
  const [question, setQuestion] = useState("")
  const submit = () => {
    if (!busy && question.trim()) void onStart(question)
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center py-10">
      <motion.div initial={{ opacity: 0.4, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h1 className="text-gradient text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
          Run an experiment. Watch it happen.
        </h1>
        <p className="mt-4 max-w-2xl text-base text-pretty text-muted-foreground">
          Jesse picks an approved simulator, operates it on screen like a lab technician, checks the measurements in
          Python and reports what the evidence supports.
        </p>
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
        <Button type="submit" size="lg" className="rounded-2xl" disabled={busy || !question.trim()}>
          {busy ? <Loader2 className="animate-spin" /> : null}
          Start experiment <ArrowRight />
        </Button>
      </form>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {EXPERIMENTS.map(({ question: example, tool, detail, icon: Icon }) => (
          <button
            key={example}
            type="button"
            onClick={() => setQuestion(example)}
            className="group flex items-start gap-3 rounded-2xl border border-border/70 bg-card/60 p-4 text-left backdrop-blur transition hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-xl hover:shadow-brand/10"
          >
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand/10 text-brand">
              <Icon className="size-4.5" />
            </span>
            <span className="flex min-w-0 flex-col gap-1">
              <span className="text-xs font-medium text-muted-foreground">{tool}</span>
              <span className="text-sm leading-snug font-medium">{example}</span>
              <span className="text-xs text-muted-foreground">{detail}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
