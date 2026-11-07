import { cn } from "@/lib/utils"

const BASE = import.meta.env.BASE_URL

/**
 * The README logo (jesse.png). Dark theme shows the original file; light theme shows the same
 * artwork with the cream "sse" recoloured to the logo green so it stays visible on white.
 */
export function Logo({ size = "sm", className }: { size?: "sm" | "lg"; className?: string }) {
  const height = size === "lg" ? "h-28 sm:h-36" : "h-8"
  return (
    <span className={cn("inline-flex", className)}>
      <img src={`${BASE}jesse-logo-light.png`} alt="Jesse" className={cn("w-auto dark:hidden", height)} />
      <img src={`${BASE}jesse-logo-dark.png`} alt="Jesse" className={cn("hidden w-auto dark:block", height)} />
    </span>
  )
}
