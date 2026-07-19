import json
from pathlib import Path

import pytest


@pytest.mark.release
def test_frozen_release_identity_and_sbom_exist():
    assert Path("LICENSE").is_file()
    assert Path("SECURITY.md").is_file()
    assert Path("CHANGELOG.md").is_file()
    sbom = json.loads(Path("sbom.json").read_text(encoding="utf-8"))
    assert sbom["bomFormat"] == "CycloneDX"
