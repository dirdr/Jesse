"""One hosted operator, local calorimetry tools and retained public updates."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

from jesse.runtime import conversation_event, json_value, save_json
from .domain import ACTIVITY_URL, analyze_reading


class CoolantRecords:
    def __init__(self, folder: Path):
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "observations").mkdir(exist_ok=True)

    def record(self, reading: dict) -> dict:
        trial_id = reading["trial_id"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", trial_id):
            raise ValueError("Use a stable safe trial identifier")
        analysis = analyze_reading(reading)
        path = self.folder / "observations" / f"{trial_id}.json"
        if path.exists():
            original = json.loads(path.read_text())
            if original["reading"] != reading:
                raise ValueError("Conflicting retry: preserve the original trial")
        else:
            if len(list(path.parent.glob("*.json"))) >= 2:
                raise ValueError("The two-trial limit has been reached")
            save_json(path.parent, path.name, {"recorded_at": datetime.now(timezone.utc).isoformat(), "reading": reading})
            conversation_event(self.folder, "measurement", f"Saved {trial_id}: final temperature {reading['final_c']:g} °C.")
        save_json(self.folder, f"analysis-{trial_id}.json", analysis)
        return {"recorded": True, **analysis}

    def finish(self, reason: str) -> str:
        readings = sorted((self.folder / "observations").glob("*.json"))
        outcome = "inconclusive" if readings else "blocked"
        analyses = [json.loads(path.read_text()) for path in sorted(self.folder.glob("analysis-*.json"))]
        estimates = [item["specific_heat_j_g_c"] for item in analyses if item["status"] == "estimated"]
        verification = {"estimated_trials": len(estimates), "replay_review": "pending"}
        if len(estimates) == 2:
            verification["absolute_difference_j_g_c"] = abs(estimates[1] - estimates[0])
        save_json(self.folder, "verification.json", verification)
        save_json(self.folder, "outcome.json", {"outcome": outcome, "reason": reason,
                  "recorded_trials": len(readings), "verification": "pending_replay_review"})
        rows = []
        for item in analyses:
            value = item["specific_heat_j_g_c"]
            rows.append(f"| {item['trial_id']} | {value:.5g} | {item['comparison']} |" if value is not None else f"| {item['trial_id']} | Not calculated | Conditions need a repeat |")
        session_path = self.folder / "session.json"
        session = json.loads(session_path.read_text()) if session_path.exists() else {}
        source = "https://chemcollective.org/activities/info/92"
        text = (f"# Coolant investigation\n\nOutcome: **{outcome}**\n\n{reason}\n\n"
                "This experimental protocol estimates Compound Y's heat capacity and compares it with the assignment's supplied ethylene glycol reference, **2.200 J/(g·°C)**. The reference is not a separately performed GUI trial.\n\n"
                "| Trial | Specific heat, J/(g·°C) | Preliminary comparison |\n| --- | --- | --- |\n"
                + "\n".join(rows) + "\n\n"
                "Calculation: c_Y = m_water × 4.184 × (T_water − T_final) / [m_Y × (T_final − T_Y)].\n\n"
                "Assumptions: water density approximated as 1.00 g/mL; supplied coolant density 2.78 g/mL; negligible container heat capacity and mixing enthalpy; insulated samples and vessel. Actual initial temperatures must be stable immediately before mixing.\n\n"
                "Verification: fresh repeat and replay evidence must be reviewed before accepting a conclusion. Two matching estimates alone do not establish statistical confidence or physical coolant performance. Agent narrative is stored separately and is unverified.\n\n"
                f"[Scenario source]({source}) · [Protocol](protocol.md) · [Verification](verification.json)\n\n")
        for path in readings:
            trial_id = path.stem
            text += f"- [{trial_id}: raw reading](observations/{path.name}) · [Analysis](analysis-{trial_id}.json)\n"
        if session.get("agent_view_url"):
            text += f"\n[H session and replay]({session['agent_view_url']})\n"
        (self.folder / "report.md").write_text(text, encoding="utf-8")
        return outcome


def execute(folder: Path, budget_seconds: int, interactive: bool = False, client=None) -> None:
    from hai_agents import Client

    records = CoolantRecords(folder)
    started = time.monotonic()
    handle = None

    def record_calorimetry(trial_id: str, coolant_volume_ml: float, water_volume_ml: float,
                          coolant_initial_c: float, water_initial_c: float, final_c: float,
                          samples_insulated: bool, mixing_vessel_insulated: bool,
                          temperatures_verified: bool, raw_reading: str, evidence: list[str]) -> dict:
        """Save actual observed volumes/temperatures and return checked Python analysis.

        samples_insulated means BOTH separate samples were insulated before initial
        readings. temperatures_verified means actual initial temperatures were stable
        and checked immediately before mixing. Report false when uncertain. Preserve
        evidence references and raw readings. The controller approximates water density
        as 1.00 g/mL. At most two independent physical mixing trials are allowed.
        """
        return records.record(dict(trial_id=trial_id, coolant_volume_ml=coolant_volume_ml,
            water_volume_ml=water_volume_ml, coolant_initial_c=coolant_initial_c,
            water_initial_c=water_initial_c, final_c=final_c, samples_insulated=samples_insulated,
            mixing_vessel_insulated=mixing_vessel_insulated, temperatures_verified=temperatures_verified,
            raw_reading=raw_reading, evidence=evidence))

    def publish_update(update_id: str, kind: str, text: str) -> dict:
        """Tell the researcher a concise plan, finding, follow_up or blocker.

        Use one or two accessible sentences at meaningful milestones. No narration
        of routine clicks or private reasoning. Keep a stable update_id on retries.
        """
        if kind not in {"plan", "finding", "follow_up", "blocker"} or not 1 <= len(text.strip()) <= 1000:
            raise ValueError("Supply an allowed kind and 1–1000 characters")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", update_id):
            raise ValueError("Use a safe update identifier")
        updates = folder / "updates"
        updates.mkdir(exist_ok=True)
        path = updates / f"{update_id}.json"
        payload = {"kind": kind, "text": text}
        if path.exists():
            if json.loads(path.read_text()) != payload:
                raise ValueError("Conflicting update retry")
        else:
            conversation_event(folder, kind, text, speak=True)
            save_json(updates, path.name, payload)
        return {"published": True}

    def acknowledge_researcher_message(event_id: str, status: str, text: str) -> dict:
        """Acknowledge a researcher message as acknowledged, applied or rejected.

        Read the message ID supplied with its text. Say applied only after checking
        the requested change actually took effect; explain a rejected change. Preserve
        original measurements and the fixed scope, two-trial limit and time budget.
        """
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", event_id) or status not in {"acknowledged", "applied", "rejected"} or not 1 <= len(text.strip()) <= 1000:
            raise ValueError("Invalid researcher acknowledgement")
        path = folder / "messages" / f"{event_id}.json"
        if not path.exists():
            raise ValueError("Unknown researcher message ID")
        receipt = folder / "messages" / f"{event_id}-{status}.json"
        if not receipt.exists():
            conversation_event(folder, status, text, speak=True, message_id=event_id)
            save_json(receipt.parent, receipt.name, {"status": status, "text": text})
        return {"recorded": True, "status": status}

    try:
        handle = (client or Client(timeout=30)).start_session(agent={
            "name": "jesse-chemcollective-coolant", "description": "Experimental GUI calorimetry with evidence and researcher interaction",
            "model": "holo4-27b", "reasoning_effort": "low", "environments": [{"id": "coolant-browser", "kind": "web", "start_url": ACTIVITY_URL,
                "mode": {"type": "visual", "width": 1440, "height": 1000}}]},
            messages=(folder / "protocol.md").read_text(encoding="utf-8"),
            tools=[record_calorimetry, publish_update, acknowledge_researcher_message],
            max_time_s=budget_seconds, max_steps=110, **({"idle_timeout_s": 90} if interactive else {}))
        save_json(folder, "session.json", {"id": handle.id, "agent_view_url": None})
        metadata = handle.get()
        save_json(folder, "session.json", {"id": handle.id, "agent_view_url": metadata.agent_view_url})
        print(f"Agent View: {metadata.agent_view_url}", flush=True)
        conversation_event(folder, "session", "The laboratory is opening. You can watch the experiment in H Agent View.")
        for event in handle.stream(timeout_seconds=max(1, budget_seconds - (time.monotonic() - started)), wait_for_seconds=5,
                                   until="terminal" if interactive else "settled"):
            payload = json_value(event)
            with (folder / "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(payload, allow_nan=False) + "\n")
            data = payload.get("data") or {}
            if data.get("kind") == "answer_event":
                (folder / "agent-report.md").write_text(str(data.get("answer", "")), encoding="utf-8")
                records.finish("The agent answered; measurements and verification require replay review.")
                if interactive:
                    conversation_event(folder, "waiting", "My current report is ready. You can ask a follow-up while this session remains open.")
            if payload.get("type") == "ActiveStateChangeEvent":
                save_json(folder, "session-state.json", {"state": data.get("state")})
        result = handle.wait_for_completion(timeout_seconds=5)
        save_json(folder, "session.json", {**json_value(result), "id": handle.id, "agent_view_url": metadata.agent_view_url})
        (folder / "agent-report.md").write_text(str(result.answer or "No final agent answer."), encoding="utf-8")
        records.finish("Session finished. Current protocol remains experimental; review measurements, repeat and replay before accepting a conclusion.")
    except (KeyboardInterrupt, TimeoutError) as error:
        records.finish("The run was stopped or reached its time budget; earlier evidence is retained.")
        if isinstance(error, KeyboardInterrupt):
            raise
    except Exception as error:
        save_json(folder, "error.json", {"type": type(error).__name__})
        records.finish(f"Execution stopped ({type(error).__name__}); prior evidence is retained.")
    finally:
        if handle is not None:
            try:
                handle.cancel()
            except Exception as error:
                save_json(folder, "cleanup.json", {"cancellation": "failed", "error_type": type(error).__name__})
        conversation_event(folder, "finished", "The session has closed. The report includes the measurements and remaining limitations.", speak=True)
