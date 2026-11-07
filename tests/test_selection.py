"""Catalogue selection is checked before any simulator is launched."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from jesse.selecting.application import select_experiment
from jesse.selecting.domain import CATALOGUE, Proposal
from jesse.selecting.domain import PlannerUnavailable
from jesse.selecting.adapters import PlannerOutput, PydanticExperimentPlanner


class FakePlanner:
    def __init__(self, proposal):
        self.proposal = proposal
        self.calls = 0

    def propose(self, question, catalogue, available_surfaces, requested_surface):
        self.calls += 1
        self.available_surfaces = available_surfaces
        return self.proposal


class SelectionTests(unittest.TestCase):
    def test_supported_question_selects_a_registered_bounded_protocol(self):
        planner = FakePlanner(Proposal("select", CATALOGUE[0].experiment_id, "web", "Compare substrate settings in a preliminary assay."))
        selected = select_experiment("Does more substrate change the rate?", CATALOGUE, {"web"}, planner)
        self.assertEqual(selected.status, "ready")
        self.assertEqual(selected.maximum_trials, 2)
        self.assertEqual(selected.surface, "web")

    def test_unsupported_question_is_blocked(self):
        planner = FakePlanner(Proposal("blocked", None, None, "No coolant assay is registered."))
        selected = select_experiment("Measure coolant heat capacity", CATALOGUE, {"web"}, planner)
        self.assertEqual(selected.status, "blocked")
        self.assertIsNone(selected.experiment_id)

    def test_unregistered_experiments_and_unavailable_surfaces_are_rejected(self):
        for proposal in (
            Proposal("select", "invented-app", "web", "Use another app."),
            Proposal("select", CATALOGUE[0].experiment_id, "desktop", "Use desktop."),
            Proposal("select", CATALOGUE[0].experiment_id, "web", ""),
        ):
            with self.subTest(proposal=proposal):
                selected = select_experiment("Compare rates", CATALOGUE, {"web"}, FakePlanner(proposal))
                self.assertEqual(selected.status, "blocked")

    def test_explicit_surface_preference_is_enforced(self):
        planner = FakePlanner(Proposal("select", CATALOGUE[0].experiment_id, "web", "Use web."))
        selected = select_experiment("Compare rates", CATALOGUE, {"web", "desktop"}, planner, "desktop")
        self.assertEqual(selected.status, "blocked")
        self.assertEqual(planner.available_surfaces, {"desktop"})

    def test_no_available_surface_does_not_call_the_planner(self):
        planner = FakePlanner(None)
        selected = select_experiment("Compare rates", CATALOGUE, set(), planner)
        self.assertEqual(selected.status, "blocked")
        self.assertEqual(planner.calls, 0)

    def test_invalid_question_and_empty_catalogue_do_not_call_the_planner(self):
        for question, catalogue in ((" ", CATALOGUE), ("x" * 4001, CATALOGUE), ("Compare rates", ())):
            planner = FakePlanner(None)
            self.assertEqual(select_experiment(question, catalogue, {"web"}, planner).status, "blocked")
            self.assertEqual(planner.calls, 0)

    def test_provider_quota_failure_is_reported_without_request_or_key_details(self):
        from pydantic_ai.exceptions import ModelQuotaExceededError
        error = ModelQuotaExceededError("test-model", "sensitive provider details", body={"secret": "synthetic-key"})
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), patch("pydantic_ai.Agent.run_sync", side_effect=error):
            with self.assertRaises(PlannerUnavailable) as raised:
                PydanticExperimentPlanner().propose("Compare rates", CATALOGUE, {"web"}, "auto")
        self.assertIn("credits", str(raised.exception))
        self.assertNotIn("synthetic-key", str(raised.exception))
        self.assertNotIn("sensitive", str(raised.exception))

    def test_provider_adapter_returns_the_typed_proposal(self):
        from pydantic_ai.usage import RunUsage
        output = PlannerOutput(decision="select", experiment_id=CATALOGUE[0].experiment_id, surface="web", reason="A bounded preliminary comparison is available.")
        result = SimpleNamespace(output=output, usage=RunUsage())
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-key"}), patch("pydantic_ai.Agent.run_sync", return_value=result):
            proposed = PydanticExperimentPlanner().propose("Compare rates", CATALOGUE, {"web"}, "auto")
        self.assertEqual(proposed.surface, "web")

    def test_h_selector_uses_a_catalogue_tool_without_provisioning_a_gui(self):
        from jesse.selecting.adapters import HExperimentPlanner
        from hai_agents.tools import as_tools

        class Handle:
            id = "synthetic-planner-session"
            cancelled = False

            def get(self):
                return SimpleNamespace(agent_view_url="https://example.test/planner")

            def stream(self, **kwargs):
                payload = self.catalogue_tool()
                self.catalogue = payload
                yield {"type": "SyntheticPlannerEvent"}

            def wait_for_completion(self, **kwargs):
                return SimpleNamespace(status="completed", answer=PlannerOutput(decision="select", experiment_id=CATALOGUE[0].experiment_id, surface="web", reason="Supported preliminary comparison."))

            def cancel(self):
                self.cancelled = True

        handle = Handle()

        class Client:
            def start_session(self, **params):
                self.params = params
                handle.catalogue_tool = as_tools(params["tools"])[0]
                return handle

        client = Client()
        selection = select_experiment("Compare substrate rates", CATALOGUE, {"web"}, HExperimentPlanner(client=client))
        self.assertEqual(selection.status, "ready")
        self.assertEqual(client.params["agent"]["environments"], [])
        self.assertEqual(handle.catalogue["available_surfaces"], ["web"])
        self.assertTrue(handle.cancelled)
