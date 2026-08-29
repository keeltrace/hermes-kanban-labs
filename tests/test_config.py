from pathlib import Path
import pytest

from hermes_kanban_labs.config import load_config


def test_example_has_standalone_and_cluster():
    cfg = load_config(Path(__file__).parents[1] / "examples" / "workers.toml")
    assert cfg.workers["mac-mini-01"].kind == "standalone"
    monster = cfg.workers["monster-shard"]
    assert monster.kind == "shard_cluster"
    assert monster.cluster_nodes == 20
    assert monster.backend == "ssh-docker"


def test_ssh_worker_requires_target(tmp_path):
    p = tmp_path / "x.toml"
    p.write_text('[workers.bad]\nbackend="ssh-docker"\n')
    with pytest.raises(ValueError, match="ssh is required"):
        load_config(p)
