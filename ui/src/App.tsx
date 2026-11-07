import { useEffect, useState } from "react"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Header } from "@/components/header"
import { Launcher } from "@/components/launcher"
import { LiveScreen } from "@/components/live-screen"
import { MeasurementsPanel, PlanPanel } from "@/components/side-panels"
import { SteerBar } from "@/components/steer-bar"
import { OutcomeBadge, ReportSheet } from "@/components/details"
import { useRun } from "@/lib/use-run"
import { useVoice } from "@/lib/use-voice"
import { TranscriptPill, VoiceButton } from "@/components/voice"

export default function App() {
  const run = useRun()
  const voice = useVoice((runId) => {
    window.history.replaceState(null, "", window.location.pathname)
    run.attach(runId, false)
  })
  const mic = <VoiceButton state={voice.state} onToggle={voice.toggle} />
  const [pinned, setPinned] = useState<number | null>(null)
  const [reportOpen, setReportOpen] = useState(false)
  const hasRun = run.runId !== null
  const live = run.live
  const snapshot = run.snapshot
  const finished = Boolean(snapshot && !snapshot.active)

  useEffect(() => {
    setPinned(null)
    setReportOpen(false)
  }, [run.runId])

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex min-h-full flex-col">
        <Header
          snapshot={snapshot}
          hasRun={hasRun}
          replay={run.replay}
          reportReady={Boolean(run.report)}
          onStop={run.stop}
          onNew={run.reset}
          onReport={() => setReportOpen(true)}
          mic={hasRun ? mic : null}
        />

        {!hasRun ? (
          <main className="flex flex-1 px-4 sm:px-6">
            <Launcher busy={run.busy} onStart={run.start} mic={mic} />
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
                <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border/70 bg-card/70 px-4 py-3 backdrop-blur">
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
      <TranscriptPill state={voice.state} />
      <ReportSheet open={reportOpen} onOpenChange={setReportOpen} snapshot={snapshot} report={run.report} />
      <Toaster position="top-center" richColors />
    </TooltipProvider>
  )
}
