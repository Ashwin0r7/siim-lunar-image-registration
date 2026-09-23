"""``sample_images/`` is what its manifest says it is.

Every committed sample file's SHA-256 matches the manifest, every scenario
README quotes the live result recorded for it, the expected outcomes are the
ones the folder advertises (a pair that registers, two triplets that reach
VERIFIED, two pairs the system must refuse), and no Chandrayaan-2 pixel is
committed.
"""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "sample_images"
MAN = S / "manifest.json"

pytestmark = pytest.mark.skipif(not MAN.exists(), reason="sample_images not built")


def _man():
    return json.loads(MAN.read_text(encoding="utf-8"))


def test_every_file_matches_its_digest():
    for sc in _man()["scenarios"]:
        for f in sc["files"]:
            p = S / sc["id"] / f["file"]
            assert hashlib.sha256(p.read_bytes()).hexdigest() == f["sha256"], p


def test_the_advertised_outcomes():
    got = {sc["id"]: sc["live_check"]["status"] for sc in _man()["scenarios"]}
    assert got["01_pair_registers_small_sun_change"] == "INCONCLUSIVE"
    assert got["02_triplet_reaches_VERIFIED"] == "VERIFIED"
    assert got["04_held_out_site_triplet"] == "VERIFIED"
    assert got["03_illumination_refusal"] == "REJECTED"
    assert got["06_unrelated_ground_must_refuse"] == "REJECTED"
    for sc in _man()["scenarios"]:
        if sc["live_check"]["status"] == "REJECTED":
            assert sc["live_check"].get("registered_image_emitted") is False


def test_each_readme_quotes_its_live_result_and_credit():
    index = (S / "README.md").read_text(encoding="utf-8")
    assert "NASA/GSFC/Arizona State University" in index and "JAXA" in index
    for sc in _man()["scenarios"]:
        text = (S / sc["id"] / "README.md").read_text(encoding="utf-8")
        live = sc["live_check"]
        assert f"**{live['status']} / {live['confidence']}**" in text
        assert "not a recorded stage number" in text


def test_no_chandrayaan2_pixels_are_tracked():
    out = subprocess.run(["git", "ls-files", "sample_images"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    assert "_local_chandrayaan2" not in out
    for sc in _man()["scenarios"]:
        for f in sc["files"]:
            assert "Chandrayaan" not in f["instrument"]
