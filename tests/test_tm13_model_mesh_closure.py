import json
from pathlib import Path

from flowguard_models.model_mesh import run_mesh


def test_current_parent_child_mesh_closure_is_green():
    path = Path(
        ".flowguard/evidence/model_mesh/MM0_matters_parent_child_mesh.json"
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))
    current = run_mesh()
    assert persisted["status"] == "mesh_green"
    assert persisted["mesh_fingerprint"] == current["mesh_fingerprint"]
    assert persisted["native_report"]["ok"]
    assert not persisted["unbound_outputs"]
