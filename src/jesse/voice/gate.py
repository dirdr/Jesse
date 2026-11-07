"""Near-field voice gate: pass only speech clearly louder than the room, send silence otherwise.

Speech-to-text services transcribe every voice they receive. Distant voices and room chatter reach the microphone
much quieter than the person speaking into it, so blocks below an adaptive noise floor plus a margin are zeroed
before they leave the machine.
"""
from array import array
from collections import deque
import math

FLOOR_WINDOW = 75      # blocks of history (15 s at 200 ms) used to estimate the room level
FLOOR_PERCENTILE = 0.2  # the room level is what most blocks exceed; tolerates long pauses in speech
MARGIN_DB = 15.0        # how much louder than the room a block must be to count as the near speaker
MINIMUM_DB = -55.0      # never open below this, even in a silent room
HANGOVER_BLOCKS = 4     # keep open briefly after speech so word endings are not clipped
WARMUP_BLOCKS = 5       # listen to the room for 1 s before letting anything through


def level_db(block: bytes) -> float:
    samples = array("h")
    samples.frombytes(block[: len(block) - len(block) % 2])
    if not samples:
        return -120.0
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    return 20 * math.log10(max(rms, 1.0) / 32768)


class VoiceGate:
    def __init__(self, *, margin_db: float = MARGIN_DB, minimum_db: float = MINIMUM_DB):
        self.margin_db = margin_db
        self.minimum_db = minimum_db
        self.history: deque[float] = deque(maxlen=FLOOR_WINDOW)
        self.hold = 0
        self.level = -120.0
        self.open = False

    @property
    def floor(self) -> float:
        if not self.history:
            return -120.0
        ordered = sorted(self.history)
        return ordered[int(FLOOR_PERCENTILE * (len(ordered) - 1))]

    @property
    def threshold(self) -> float:
        return max(self.floor + self.margin_db, self.minimum_db)

    def process(self, block: bytes) -> bytes:
        self.level = level_db(block)
        if len(self.history) < WARMUP_BLOCKS:
            self.history.append(self.level)
            self.open = False
            return bytes(len(block))
        loud = self.level >= self.threshold
        self.history.append(self.level)
        self.hold = HANGOVER_BLOCKS if loud else max(0, self.hold - 1)
        self.open = loud or self.hold > 0
        return block if self.open else bytes(len(block))
