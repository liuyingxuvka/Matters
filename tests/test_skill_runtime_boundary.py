import ast
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1] / "src" / "matters" / "skills"
FORBIDDEN_CANONICAL_MODULES = {
    "matters.domain",
    "matters.state",
    "matters.provenance",
    "matters.identity",
    "matters.timeline",
    "matters.revisions",
    "matters.presentation",
    "matters.application",
}


def test_skill_runtime_has_zero_canonical_matter_imports_or_writers():
    imported: set[str] = set()
    assignment_names: set[str] = set()
    for path in SKILL_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assignment_names.add(node.name)
    assert not {
        module
        for module in imported
        if any(
            module == forbidden or module.startswith(forbidden + ".")
            for forbidden in FORBIDDEN_CANONICAL_MODULES
        )
    }
    assert not {
        "write_matter",
        "write_lifecycle",
        "write_outcome",
        "write_evidence",
        "write_projection",
    } & assignment_names


def test_skill_runtime_source_contains_no_author_side_control_payload():
    forbidden_parts = {
        ".skillguard",
        "compiled-contract.json",
        "contract-source.json",
        "check-manifest.json",
        "global_registry.json",
    }
    product_paths = {
        path.relative_to(SKILL_ROOT).as_posix()
        for path in SKILL_ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert not forbidden_parts & product_paths
