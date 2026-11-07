import { ExternalLink, FlaskConical, Plus, Square, Volume2, VolumeX } from "lucide-react"
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
import type { Snapshot } from "@/lib/api"

interface HeaderProps {
  snapshot: Snapshot | null
  hasRun: boolean
  voiceOn: boolean
  onToggleVoice: () => void
  onStop: () => void
  onNew: () => void
}

export function Header({ snapshot, hasRun, voiceOn, onToggleVoice, onStop, onNew }: HeaderProps) {
  const speechAvailable = typeof window !== "undefined" && "speechSynthesis" in window
  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between gap-3 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-brand to-brand-2 text-white shadow-lg shadow-brand/25">
            <FlaskConical className="size-4" />
          </div>
          <span className="text-[15px] font-semibold tracking-tight">Jesse</span>
          <span className="hidden text-sm text-muted-foreground sm:inline">Research technician</span>
          <span className="hidden h-4 w-px bg-border sm:block" />
          <StatusBadge status={snapshot?.status ?? "idle"} />
        </div>

        <div className="flex items-center gap-1.5">
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
            <Button variant="outline" size="sm" asChild>
              <a href={snapshot.agent_view_url} target="_blank" rel="noopener noreferrer">
                Watch live <ExternalLink />
              </a>
            </Button>
          )}

          {snapshot?.active && (
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
                    Jesse stops the simulator session. Measurements recorded so far are kept and the report is marked
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

          {hasRun && !snapshot?.active && (
            <Button size="sm" onClick={onNew}>
              <Plus /> New investigation
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
