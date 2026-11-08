import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

const PHOTO = `${import.meta.env.BASE_URL}jesse-pinkman.png`
const JAW = "polygon(30% 50%, 64% 50%, 63% 58%, 56% 64.5%, 47% 66.5%, 38% 64%, 31% 57%)"
const SHAPES = [0, 0.35, 0.7, 1, 0.5, 0.15]

export function TalkingJesse({ speaking }: { speaking: string | null }) {
  const [open, setOpen] = useState(0)
  const [tilt, setTilt] = useState(0)
  const talking = Boolean(speaking)

  useEffect(() => {
    if (!talking) {
      setOpen(0)
      setTilt(0)
      return
    }
    let tick = 0
    const flap = window.setInterval(() => {
      tick += 1
      setOpen(SHAPES[Math.floor(Math.random() * SHAPES.length)])
      if (tick % 2 === 0) setTilt((value) => (value > 0 ? -7 : 7))
    }, 110)
    return () => window.clearInterval(flap)
  }, [talking])

  return (
    <div className="pointer-events-none fixed right-4 bottom-4 z-40 flex items-end gap-2 sm:right-6 sm:bottom-6">
      <div
        role="img"
        aria-label="Jesse Pinkman"
        className={cn(
          "relative aspect-[273/365] w-24 origin-bottom overflow-hidden rounded-[45%_45%_40%_40%] border-[3px] border-foreground bg-black shadow-[4px_4px_0_0_var(--brand)] sm:w-32",
          !speaking && "opacity-80",
        )}
        style={{ transform: `translateY(${talking ? -open * 14 : 0}px) rotate(${tilt}deg) scale(${1 + open * 0.07}, ${1 - open * 0.05})` }}
      >
        <img src={PHOTO} alt="" draggable={false} className="pointer-events-none absolute inset-0 size-full select-none" />
        <span
          className="absolute rounded-[50%] bg-[#2a0a0a]"
          style={{
            left: "37%",
            top: "49%",
            width: "20%",
            height: "9%",
            transformOrigin: "top",
            transform: `scaleY(${open})`,
            boxShadow: "inset 0 -2px 0 #b33",
          }}
        />
        <img
          src={PHOTO}
          alt=""
          draggable={false}
          className="pointer-events-none absolute inset-0 size-full select-none"
          style={{ clipPath: JAW, transform: `translateY(${open * 7}%)` }}
        />
      </div>
    </div>
  )
}
