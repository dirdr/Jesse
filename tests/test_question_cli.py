"""Question routing must validate a plan before dispatching computer use."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jesse.selecting.cli import main
from jesse.selecting.domain import CATALOGUE, PlannerUnavailable, Proposal
from jesse.experiments.netlogo.preflight import Check


class Planner:
    usage = {}

    def __init__(self, proposal):
        self.proposal = proposal

    def propose(self, *args):
        if isinstance(self.proposal, Exception):
            raise self.proposal
        return self.proposal


@contextmanager
def workspace():
    previous = Path.cwd()
    with tempfile.TemporaryDirectory() as folder:
        os.chdir(folder)
        try:
            yield Path(folder)
        finally:
            os.chdir(previous)


def setup_check(explicit, surface):
    return [Check("synthetic-availability", surface == "web", "Synthetic setup check")], None


class QuestionCliTests(unittest.TestCase):
    def test_selected_protocol_reuses_run_folder_and_preserves_question(self):
        planner = Planner(Proposal("select", CATALOGUE[0].experiment_id, "web", "A preliminary rate comparison is supported."))
        with workspace() as root, patch("jesse.selecting.cli.check_desktop", side_effect=setup_check), patch("jesse.selecting.cli.PydanticExperimentPlanner", return_value=planner), patch("jesse.selecting.cli.run_ready_experiment", return_value=0) as execute:
            self.assertEqual(main(["Does more substrate increase the rate?"]), 0)
            folder = next((root / "runs").iterdir())
            args = execute.call_args.args
            self.assertEqual(args[0].resolve(), folder.resolve())
            self.assertEqual(args[3], "web")
            self.assertEqual(args[4], "Does more substrate increase the rate?")
            self.assertLessEqual(args[1], 300)
            self.assertEqual(json.loads((folder / "selection.json").read_text())["status"], "ready")

    def test_unsupported_question_never_launches_h_operator(self):
        planner = Planner(Proposal("blocked", None, None, "No coolant protocol is registered."))
        with workspace() as root, patch("jesse.selecting.cli.check_desktop", side_effect=setup_check), patch("jesse.selecting.cli.PydanticExperimentPlanner", return_value=planner), patch("jesse.selecting.cli.run_ready_experiment") as execute:
            self.assertEqual(main(["Measure a coolant"]), 1)
            execute.assert_not_called()
            folder = next((root / "runs").iterdir())
            self.assertEqual(json.loads((folder / "outcome.json").read_text())["outcome"], "blocked")
            self.assertFalse((folder / "session.json").exists())

    def test_plan_only_never_operates_simulator(self):
        planner = Planner(Proposal("select", CATALOGUE[0].experiment_id, "web", "A preliminary comparison is available."))
        with workspace(), patch("jesse.selecting.cli.check_desktop", side_effect=setup_check), patch("jesse.selecting.cli.PydanticExperimentPlanner", return_value=planner), patch("jesse.selecting.cli.run_ready_experiment") as execute:
            self.assertEqual(main(["Compare rates", "--plan-only"]), 0)
            execute.assert_not_called()

    def test_provider_failure_produces_blocked_report(self):
        planner = Planner(PlannerUnavailable("OpenAI credits are unavailable."))
        with workspace() as root, patch("jesse.selecting.cli.check_desktop", side_effect=setup_check), patch("jesse.selecting.cli.PydanticExperimentPlanner", return_value=planner), patch("jesse.selecting.cli.run_ready_experiment") as execute:
            self.assertEqual(main(["Compare rates"]), 1)
            execute.assert_not_called()
            folder = next((root / "runs").iterdir())
            self.assertIn("credits", (folder / "report.md").read_text())

    def test_catalogue_can_be_listed_without_provider_or_preflight(self):
        with patch("jesse.selecting.cli.PydanticExperimentPlanner") as planner, patch("jesse.selecting.cli.check_desktop") as preflight:
            self.assertEqual(main(["--catalogue"]), 0)
            planner.assert_not_called()
            preflight.assert_not_called()
