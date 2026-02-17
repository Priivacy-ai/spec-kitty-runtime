from spec_kitty_runtime.planner import plan_next
from spec_kitty_runtime.schema import MissionPolicySnapshot, MissionRunSnapshot, MissionTemplate


def _template() -> MissionTemplate:
    return MissionTemplate.model_validate(
        {
            "mission": {
                "key": "software-dev",
                "name": "Software Development",
                "version": "1.0.0",
                "description": "",
            },
            "steps": [
                {"id": "S1", "title": "Step One", "prompt": "Do one"},
                {"id": "S2", "title": "Step Two", "prompt": "Do two", "depends_on": ["S1"]},
            ],
        }
    )


def test_planner_is_deterministic_for_same_snapshot() -> None:
    template = _template()
    snapshot = MissionRunSnapshot(
        run_id="r1",
        mission_key="software-dev",
        template_path="/tmp/mission.yaml",
        step_index=0,
        issued_step_id=None,
        completed_steps=[],
        inputs={},
        decisions={},
        blocked_reason=None,
    )
    policy = MissionPolicySnapshot()

    d1 = plan_next(snapshot, template, policy)
    d2 = plan_next(snapshot, template, policy)

    assert d1.model_dump() == d2.model_dump()
    assert d1.kind == "step"
    assert d1.step_id == "S1"
