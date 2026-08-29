from pathlib import Path
from types import SimpleNamespace

from hermes_kanban_labs.config import load_config
from hermes_kanban_labs.policy import resolve_execution_policy


def test_policy_precedence_global_board_workflow_nested_path_then_card(tmp_path):
    cfgp = tmp_path / "workers.toml"
    cfgp.write_text('''
[policy]
model = "global-model"
prompt = "global prompt"
max_open_cards = 40

[boards.default]
model = "board-model"
prompt = "board prompt"
max_open_cards = 30
max_ready_cards = 8

[boards.default.paths."research"]
model = "research-model"
prompt = "research prompt"
max_children_per_card = 5

[boards.default.paths."research.deep"]
reasoning_effort = "medium"
prompt = "deep prompt"

[boards.default.workflows.release]
provider = "workflow-provider"
prompt = "release prompt"

[boards.default.workflows.release.paths."research.deep"]
model = "workflow-path-model"
reasoning_effort = "high"
prompt = "workflow deep prompt"
max_depth = 4

[workers.remote]
backend = "ssh-docker"
ssh = "u@h"
model = "worker-model"
provider = "worker-provider"
''')
    cfg = load_config(cfgp)
    task = SimpleNamespace(
        workflow_template_id="release",
        current_step_key="research.deep.compare",
        model_override="card-model",
        provider_override="card-provider",
        reasoning_effort="xhigh",
        skills=["git", "tests", "git"],
    )
    p = resolve_execution_policy(cfg, cfg.workers["remote"], task, "default")
    assert p.model == "card-model"
    assert p.provider == "card-provider"
    assert p.reasoning_effort == "xhigh"
    assert p.skills == ("git", "tests")
    assert p.max_open_cards == 30
    assert p.max_ready_cards == 8
    assert p.max_children_per_card == 5
    assert p.max_depth == 4
    assert p.prompt_layers == (
        "global prompt", "board prompt", "release prompt", "research prompt",
        "deep prompt", "workflow deep prompt",
    )
    assert p.sources[-3:] == (
        "card:model_override", "card:provider_override", "card:reasoning_effort"
    )
