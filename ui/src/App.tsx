import { useEffect, useRef, useState } from "react"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Header } from "@/components/header"
import { Welcome } from "@/components/welcome"
import { Feed } from "@/components/feed"
import { Composer } from "@/components/composer"
import { Details } from "@/components/details"
import { useRun } from "@/lib/use-run"

declare global {
  interface Window {
    /** Entry point for a voice adapter (e.g. Gladia): call once per final transcript. */
    jesseSubmit?: (text: string, source?: "text" | "voice") => Promise<boolean>
  }
}

export default function App() {
  const run = useRun()
  const [draft, setDraft] = useState("")
  const scroller = useRef<HTMLDivElement>(null)
  const hasRun = run.runId !== null
  const events = run.snapshot?.events ?? []
  const lastAuthor = events.at(-1)?.author
  const working = Boolean(run.snapshot?.active && run.snapshot.status !== "waiting" && lastAuthor !== "jesse")

  useEffect(() => {
    window.jesseSubmit = run.submit
    return () => {
      delete window.jesseSubmit
    }
  }, [run.submit])

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" })
  }, [events.length, working])

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex h-full flex-col">
        <Header
          snapshot={run.snapshot}
          hasRun={hasRun}
          voiceOn={run.voiceOn}
          onToggleVoice={run.toggleVoice}
          onStop={run.stop}
          onNew={() => {
            run.reset()
            setDraft("")
          }}
        />

        <main className="mx-auto grid min-h-0 w-full max-w-[1400px] flex-1 grid-cols-1 gap-6 px-4 sm:px-6 lg:grid-cols-[minmax(0,1fr)_400px]">
          <section className={"flex min-h-0 min-w-0 flex-col " + (hasRun ? "" : "lg:col-span-2")}>
            <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto">
              {hasRun ? (
                <Feed events={events} working={working} />
              ) : (
                <Welcome onPick={setDraft} />
              )}
            </div>
            <div className="pt-2 pb-4">
              <Composer
                snapshot={run.snapshot}
                hasRun={hasRun}
                busy={run.busy}
                draft={draft}
                onDraft={setDraft}
                onSubmit={run.submit}
              />
            </div>
          </section>

          {hasRun && (
            <aside className="hidden min-h-0 overflow-y-auto py-6 lg:block">
              <Details snapshot={run.snapshot} report={run.report} />
            </aside>
          )}
        </main>
      </div>
      <Toaster position="top-center" richColors />
    </TooltipProvider>
  )
}
