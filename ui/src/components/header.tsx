import { ExternalLink, FileText, Plus, Square, Volume2, VolumeX } from "lucide-react"
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
import { Logo } from "@/components/logo"
import type { Snapshot } from "@/lib/api"

interface HeaderProps {
  snapshot: Snapshot | null
  hasRun: boolean
  replay: boolean
  voiceOn: boolean
  reportReady: boolean
  onToggleVoice: () => void
  onStop: () => void
  onNew: () => void
  onReport: () => void
}

export function Header({ snapshot, hasRun, replay, voiceOn, reportReady, onToggleVoice, onStop, onNew, onReport }: HeaderProps) {
  const speechAvailable = typeof window !== "undefined" && "speechSynthesis" in window
  const question = snapshot?.events.find((event) => event.author === "researcher")?.text ?? snapshot?.selection?.question
  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-background/75 backdrop-blur-xl">
      <div className="mx-auto flex min-h-14 max-w-[1600px] flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2 sm:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <button type="button" onClick={onNew} className="shrink-0" aria-label="Jesse home">
            <Logo />
          </button>
          {hasRun && (
            <>
              <span className="hidden h-5 w-px bg-border md:block" />
              <span className="truncate text-sm font-medium" title={question}>
                {question ?? "Investigation"}
              </span>
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
