"""Near-field gate on synthetic int16 blocks."""
from array import array
import math
import unittest

from jesse.voice.gate import VoiceGate


def tone(amplitude: int, samples: int = 3200) -> bytes:
    return array("h", (int(amplitude * math.sin(i / 5)) for i in range(samples))).tobytes()


class VoiceGateTests(unittest.TestCase):
    def test_room_chatter_becomes_silence(self):
        gate = VoiceGate()
        chatter = tone(300)  # about -44 dBFS: a voice across the room
        for _ in range(30):
            out = gate.process(chatter)
        self.assertFalse(gate.open)
        self.assertEqual(out, bytes(len(chatter)))

    def test_near_voice_passes_over_chatter(self):
        gate = VoiceGate()
        for _ in range(30):
            gate.process(tone(300))
        near = tone(6000)  # about -18 dBFS: speaking into the microphone
        self.assertEqual(gate.process(near), near)

    def test_word_endings_are_kept_briefly(self):
        gate = VoiceGate()
        for _ in range(30):
            gate.process(tone(300))
        gate.process(tone(6000))
        tail = tone(300)
        self.assertEqual(gate.process(tail), tail)
        for _ in range(5):
            out = gate.process(tail)
        self.assertEqual(out, bytes(len(tail)))

    def test_silent_room_does_not_open_on_hiss(self):
        gate = VoiceGate()
        for _ in range(10):
            out = gate.process(tone(20))  # about -67 dBFS
        self.assertEqual(out, bytes(len(tone(20))))


if __name__ == "__main__":
    unittest.main()
