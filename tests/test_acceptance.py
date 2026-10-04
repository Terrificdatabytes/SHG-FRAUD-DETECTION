import json

from core.config import load_config


def test_saved_acceptance_matches_manifest():
    config = load_config()
    manifest = json.loads((config.root / "demo_cases" / "manifest.json").read_text())
    results = json.loads((config.artifacts / "acceptance.json").read_text())
    assert len(results) == len(manifest)
    for result in results:
        expected = set(manifest[result["case"]]["expected_verdict"].split("/"))
        assert result["actual"] in expected
        assert result["status"] == "PASS"
