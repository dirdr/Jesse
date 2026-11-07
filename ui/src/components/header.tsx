import { ExternalLink, FileText, FlaskConical, Globe, Monitor, Plus, Square, Volume2, VolumeX } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { StatusBadge } from "@/components/status-badge"
import { experimentName } from "@/components/details"
import type { LiveState, Snapshot } from "@/lib/api"

interface HeaderProps {
  snapshot: Snapshot | null
  live: LiveState | null
  hasRun: boolean
  replay: boolean
  voiceOn: boolean
  reportReady: boolean
  onToggleVoice: () => void
  onStop: () => void
  onNew: () => void
  onReport: () => void
}

export function Header({ snapshot, live, hasRun, replay, voiceOn, reportReady, onToggleVoice, onStop, onNew, onReport }: HeaderProps) {
  const speechAvailable = typeof window !== "undefined" && "speechSynthesis" in window
  const question = snapshot?.events.find((event) => event.author === "researcher")?.text ?? snapshot?.selection?.question
  const experiment = experimentName(snapshot?.selection?.experiment_id)
  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-background/75 backdrop-blur-xl">
      <div className="mx-auto flex min-h-14 max-w-[1600px] flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2 sm:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <button type="button" onClick={onNew} className="flex shrink-0 items-center gap-2.5" aria-label="Jesse home">
            <span className="grid size-8 place-items-center rounded-lg bg-gradient-to-br from-brand to-brand-2 text-white shadow-lg shadow-brand/25">
              <FlaskConical className="size-4" />
            </span>
            <span className="text-[15px] font-semibold tracking-tight">Jesse</span>
          </button>
          {hasRun && (
            <>
              <span className="hidden h-5 w-px bg-border md:block" />
              <div className="flex min-w-0 flex-col">
                <span className="truncate text-sm font-medium" title={question}>
                  {question ?? "Investigation"}
                </span>
                <span className="flex items-center gap-2 text-xs text-muted-foreground">
                  {experiment && (
                    <span className="inline-flex items-center gap-1">
                      {snapshot?.selection?.surface === "desktop" ? <Monitor className="size-3" /> : <Globe className="size-3" />}
                      {experiment}
                    </span>
                  )}
                  {live?.steps != null && <span className="font-mono tabular-nums">{live.steps} steps</span>}
                  {replay && <span className="font-medium text-foreground">Replay of a recorded run</span>}
                </span>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <StatusBadge status={snapshot?.status ?? "idle"} />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onToggleVoice}
                disabled={!speechAvailable}
                aria-pressed={voiceOn}
                aria-label={voiceOn ? "Mute spoken updates" : "Read updates aloud"}
              >
                {voiceOn ? <Volume2 /> : <VolumeX />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{voiceOn ? "Spoken updates on" : "Spoken updates off"}</TooltipContent>
          </Tooltip>

          {snapshot?.agent_view_url && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" asChild>
                  <a href={snapshot.agent_view_url} target="_blank" rel="noopener noreferrer" aria-label="Open in H Agent View">
                    <ExternalLink />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Open in H Agent View</TooltipContent>
            </Tooltip>
          )}

          {reportReady && (
            <Button variant="outline" size="sm" onClick={onReport}>
              <FileText /> Report
            </Button>
          )}

          {snapshot?.active && !replay && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="text-destructive hover:text-destructive">
                  <Square className="fill-current" /> Stop
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Stop this experiment?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Jesse closes the simulator session. Measurements recorded so far are kept and the report is marked
                    inconclusive.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep running</AlertDialogCancel>
                  <AlertDialogAction onClick={onStop} className="bg-destructive text-white hover:bg-destructive/90">
                    Stop experiment
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}

          {hasRun && (!snapshot?.active || replay) && (
            <Button size="sm" onClick={onNew}>
              <Plus /> New
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
