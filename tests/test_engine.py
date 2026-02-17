from pathlib import Path

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import next_step, start_mission_run
from spec_kitty_runtime.schema import MissionPolicySnapshot


def test_engine_next_loop_to_terminal(tmp_path: Path) -> None:
    mission_file = tmp_path / "pack" / "missions" / "software-dev" / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(
        """
mission:
  key: software-dev
  name: Software Development
  version: 1.0.0
  description: Test mission
steps:
  - id: S1
    title: Step One
    prompt: Do one
  - id: S2
    title: Step Two
    prompt: Do two
""",
        encoding="utf-8",
    )

    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    d1 = next_step(run, agent_id="codex", context=context)
    assert d1.kind == "step"
    assert d1.step_id == "S1"

    d2 = next_step(run, agent_id="codex", result="success", context=context)
    assert d2.kind == "step"
    assert d2.step_id == "S2"

    d3 = next_step(run, agent_id="codex", result="success", context=context)
    assert d3.kind == "terminal"
