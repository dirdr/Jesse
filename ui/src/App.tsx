import { useEffect, useState } from "react"
import { PanelLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet"
import { SidebarContent } from "@/components/sidebar"
import { useHistory } from "@/lib/use-history"
import type { RunSummary } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Header } from "@/components/header"
import { Launcher } from "@/components/launcher"
import { LiveScreen } from "@/components/live-screen"
import { MeasurementsPanel, PlanPanel } from "@/components/side-panels"
import { SteerBar } from "@/components/steer-bar"
import { OutcomeBadge, ReportSheet } from "@/components/details"
import { useRun } from "@/lib/use-run"
import { usePersonas } from "@/lib/use-personas"
import { PersonaPicker } from "@/components/persona-picker"
import { useVoice } from "@/lib/use-voice"
import { useSpeech } from "@/lib/use-speech"
import { useJesseLines } from "@/lib/use-jesse-lines"
import { TranscriptPill, VoiceButton } from "@/components/voice"
import { TalkingJesse } from "@/components/talking-jesse"

export default function App() {
  const run = useRun()
  const personas = usePersonas()
  const personaId = run.snapshot?.persona ?? personas.selected
  const voice = useVoice((runId) => {
    window.history.replaceState(null, "", window.location.pathname)
    run.attach(runId, false, true)
  })
  const speech = useSpeech(run.runId, run.snapshot?.events, run.live?.plan, run.live?.actions, Boolean(run.snapshot?.active), run.fresh, run.replay, personaId)
  const line = useJesseLines(run.runId, run.snapshot?.events, run.fresh, run.replay, speech.available && speech.on)
  const mic = <VoiceButton state={voice.state} onToggle={voice.toggle} />
  const [pinned, setPinned] = useState<number | null>(null)
  const [reportOpen, setReportOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const history = useHistory(`${run.runId}:${run.snapshot?.status ?? ""}`)
  const hasRun = run.runId !== null
  const live = run.live
  const snapshot = run.snapshot
  const finished = Boolean(snapshot && !snapshot.active)

  useEffect(() => {
    setPinned(null)
    setReportOpen(false)
  }, [run.runId])

  const openRun = (summary: RunSummary) => {
    const replay = !summary.active
    window.history.replaceState(null, "", replay ? `?run=${encodeURIComponent(summary.run_id)}` : window.location.pathname)
    run.attach(summary.run_id, replay)
    setMenuOpen(false)
  }
  const newRun = () => {
    run.reset()
    setMenuOpen(false)
  }
  const sidebar = (
    <SidebarContent
      runs={history.runs}
      contexts={history.contexts}
      pinned={history.pinned}
      selectedId={run.runId}
      onOpen={openRun}
      onNew={newRun}
    />
  )
  const menu = (
    <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMenuOpen(true)} aria-label="Past investigations">
      <PanelLeft />
    </Button>
  )

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex min-h-full">
        <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-sidebar-border lg:block">{sidebar}</aside>
        <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
          <SheetContent side="left" className="w-80 p-0">
            <SheetTitle className="sr-only">Past investigations</SheetTitle>
            {sidebar}
          </SheetContent>
        </Sheet>
        <div className="flex min-h-full min-w-0 flex-1 flex-col">
          <Header
            snapshot={snapshot}
            hasRun={hasRun}
            replay={run.replay}
            reportReady={Boolean(run.report)}
            onStop={run.stop}
            onNew={newRun}
            onReport={() => setReportOpen(true)}
            mic={hasRun ? mic : null}
            speech={speech}
            menu={menu}
            persona={<PersonaPicker state={personas} value={personaId} disabled={hasRun || run.busy || personas.pending} onSelect={(id) => void personas.select(id)} />}
          />

          {!hasRun ? (
            <main className="flex flex-1 px-4 sm:px-6">
              <Launcher busy={run.busy || personas.pending} onStart={run.start} mic={mic} />
            </main>
          ) : (
            <main className="mx-auto grid w-full max-w-[1600px] flex-1 grid-cols-1 gap-5 px-4 py-5 sm:px-6 xl:grid-cols-[minmax(0,1fr)_400px]">
              <div className="flex min-w-0 flex-col gap-4">
                <LiveScreen
                  runId={run.runId!}
                  frames={live?.frames ?? []}
                  actions={live?.actions ?? []}
                  active={Boolean(snapshot?.active)}
                  replay={run.replay}
                  pinned={pinned}
                  onPin={setPinned}
                />
                {finished && snapshot?.outcome ? (
                  <div className="flex flex-wrap items-center gap-3 rounded-md border border-border bg-card px-4 py-3">
                    <OutcomeBadge outcome={snapshot.outcome.outcome} />
                    <span className="flex-1" />
                    {run.report && (
                      <button type="button" onClick={() => setReportOpen(true)} className="text-sm font-medium text-brand hover:underline">
                        Read the report
                      </button>
                    )}
                  </div>
                ) : (
                  !run.replay && <SteerBar enabled={Boolean(snapshot?.can_message)} busy={run.busy} onSend={(text) => run.steer(text)} />
                )}
              </div>

              <aside className="flex min-w-0 flex-col gap-4 xl:sticky xl:top-[4.5rem] xl:max-h-[calc(100vh-5.5rem)]">
                <PlanPanel plan={live?.plan ?? []} />
                <MeasurementsPanel measurements={live?.measurements ?? []} />
              </aside>
            </main>
          )}
        </div>
      </div>
      <TranscriptPill state={voice.state} />
      {personaId === "pinkman" && <TalkingJesse speaking={hasRun && !run.replay ? speech.speaking ?? line : null} />}
      <ReportSheet open={reportOpen} onOpenChange={setReportOpen} snapshot={snapshot} report={run.report} />
      <Toaster position="top-center" richColors />
    </TooltipProvider>
  )
}
