import { cn } from "@/lib/utils"

/** One centered, constant-speed loader for buttons, notifications and the lab view. */
export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      data-slot="spinner"
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      className={cn("jesse-spinner size-4 shrink-0", className)}
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" opacity="0.2" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
