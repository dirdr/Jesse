"""Spoken turns start or steer investigations. No microphone, Gladia or H call is made."""
import threading
import unittest

from jesse.conversation.voice import VoiceListener


class FakeManager:
    def __init__(self, *, current=None, active=False, can_message=False):
        self.current_id = current
        self.active = active
        self.can_message = can_message
        self.started: list[str] = []
        self.messages: list[tuple] = []

    def snapshot(self, run_id):
        return {"active": self.active, "can_message": self.can_message}

    def start(self, text):
        self.started.append(text)
        self.current_id = "b" * 32
        return self.current_id

    def message(self, run_id, event_id, text, source):
        self.messages.append((run_id, text, source))


def scripted_listen(*phrases):
    def listen(on_turn, on_partial, stopping):
        for phrase in phrases:
            on_partial(phrase[:5])
            on_turn(phrase)
        stopping.wait(5)
    return listen


class VoiceListenerTests(unittest.TestCase):
    def test_turn_starts_a_run_when_idle(self):
        manager = FakeManager()
        turn = VoiceListener(manager, unavailable=lambda: None).dispatch("Does substrate speed it up?")
        self.assertEqual((turn["action"], turn["run_id"]), ("started", "b" * 32))
        self.assertEqual(manager.started, ["Does substrate speed it up?"])

    def test_turn_steers_an_active_session(self):
        manager = FakeManager(current="a" * 32, active=True, can_message=True)
        turn = VoiceListener(manager, unavailable=lambda: None).dispatch("Use volume 100")
        self.assertEqual(turn["action"], "steered")
        self.assertEqual(manager.messages, [("a" * 32, "Use volume 100", "voice")])
        self.assertEqual(manager.started, [])

    def test_turn_waits_while_session_is_opening(self):
        manager = FakeManager(current="a" * 32, active=True, can_message=False)
        turn = VoiceListener(manager, unavailable=lambda: None).dispatch("Use volume 100")
        self.assertEqual(turn["action"], "failed")
        self.assertIn("Wait", turn["detail"])
        self.assertEqual((manager.started, manager.messages), ([], []))

    def test_listen_dispatches_turns_and_stops(self):
        manager = FakeManager()
        listener = VoiceListener(manager, listen=scripted_listen("First question"), unavailable=lambda: None)
        listener.start()
        for _ in range(100):
            if listener.state()["turns"]:
                break
            threading.Event().wait(0.02)
        listener.stop()
        listener.close(timeout=5)
        state = listener.state()
        self.assertFalse(state["listening"])
        self.assertEqual([turn["action"] for turn in state["turns"]], ["started"])
        self.assertEqual(state["partial"], "")

    def test_unavailable_microphone_is_refused(self):
        listener = VoiceListener(FakeManager(), unavailable=lambda: "Set GLADIA_API_KEY")
        with self.assertRaises(ValueError):
            listener.start()
        self.assertFalse(listener.state()["available"])


if __name__ == "__main__":
    unittest.main()
