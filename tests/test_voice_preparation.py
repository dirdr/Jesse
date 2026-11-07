import contextlib
import io
import json
import os
import sys
import types
import unittest
from unittest.mock import patch

from jesse.voice.live import main
from jesse.voice.preparation import PreparedRequest, PydanticRequestPreparer


class VoicePreparationTests(unittest.TestCase):
    def test_microphone_turn_reaches_model_and_prints_preview_without_h(self):
        question = "Je souhaite une solution tampon de pH 4,76."
        prepared = PreparedRequest(
            objective="Étudier une solution tampon de pH 4,76.",
            supplied_information=["pH cible : 4,76"],
            missing_information=["Concentration totale souhaitée"],
            suggested_approach=["Vérifier le modèle approprié."],
            limitations=["Disponibilité du logiciel non vérifiée."],
        )

        def capture(client, stream_factory, *, on_turn, silence_seconds, input_device):
            on_turn(question)

        sounddevice = types.SimpleNamespace(
            query_devices=lambda *args, **kwargs: {"name": "synthetic"},
            RawInputStream=object,
            PortAudioError=type("PortAudioError", (Exception,), {}),
        )
        output = io.StringIO()
        with patch.dict(os.environ, {"GLADIA_API_KEY": "test", "OPENAI_API_KEY": "test"}, clear=True):
            with patch.dict(sys.modules, {"sounddevice": sounddevice}):
                with patch("jesse.voice.live.run_live_preview", side_effect=capture):
                    with patch("pydantic_ai.Agent.run_sync", return_value=types.SimpleNamespace(output=prepared)) as model:
                        with patch("jesse.selecting.cli.run_investigation") as execute:
                            with contextlib.redirect_stdout(output):
                                self.assertEqual(main(["--prepare"]), 0)
        self.assertEqual(json.loads(model.call_args.args[0])["transcript"], question)
        self.assertIn(question, output.getvalue())
        self.assertIn("Concentration totale souhaitée", output.getvalue())
        self.assertIn("preview only; not sent", output.getvalue())
        execute.assert_not_called()

    def test_empty_and_oversized_transcripts_are_rejected(self):
        preparer = PydanticRequestPreparer("test")
        for text in (" ", "x" * 4001):
            with self.subTest(text=text[:10]), self.assertRaises(ValueError):
                preparer.prepare(text)

    def test_prepare_requires_openai_key(self):
        with patch.dict(os.environ, {"GLADIA_API_KEY": "test"}, clear=True):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(main(["--prepare"]), 1)
        self.assertIn("OPENAI_API_KEY", output.getvalue())

    def test_prepare_and_plan_are_mutually_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                main(["--prepare", "--plan"])
        self.assertEqual(result.exception.code, 2)
