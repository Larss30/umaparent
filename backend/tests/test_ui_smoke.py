import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_page_script_loads_and_the_g1_picker_works():
    """Runs backend/tests/ui_smoke.js: loads the page script with a fake DOM and clicks through the G1 save/load flow."""
    r = subprocess.run(["node", str(Path(__file__).parent / "ui_smoke.js")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
