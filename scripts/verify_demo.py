#!/usr/bin/env python3
"""Fail closed when published demo media or its source provenance drifts."""

import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "docs" / "demo"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=ROOT, check=check, text=True, capture_output=True
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    capture = json.loads((DEMO / "capture.json").read_text())
    source = capture["recorded_source_commit"]
    if run("git", "merge-base", "--is-ancestor", source, "HEAD", check=False).returncode:
        raise SystemExit("recorded source is not an ancestor of HEAD")

    for path, expected in capture["runtime_files"].items():
        source_blob = run("git", "rev-parse", f"{source}:{path}").stdout.strip()
        head_blob = run("git", "rev-parse", f"HEAD:{path}").stdout.strip()
        if source_blob != expected["git_blob"] or head_blob != source_blob:
            raise SystemExit(f"runtime source drifted: {path}")
        if sha256(ROOT / path) != expected["sha256"]:
            raise SystemExit(f"working-tree bytes drifted: {path}")

    for name, expected in capture["artifacts"].items():
        path = DEMO / name
        if path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
            raise SystemExit(f"artifact bytes drifted: {name}")

    gif = DEMO / "bayesian-stats-demo.gif"
    with Image.open(gif) as image:
        frames = 0
        while True:
            frames += 1
            try:
                image.seek(image.tell() + 1)
            except EOFError:
                break
        if frames != 160 or image.size != (800, 450):
            raise SystemExit(f"unexpected GIF geometry/frame count: {image.size}, {frames}")

    probe = json.loads(
        run(
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,nb_read_frames,duration",
            "-of", "json", str(DEMO / "bayesian-stats-demo.mp4")
        ).stdout
    )["streams"][0]
    if (probe["width"], probe["height"], int(probe["nb_read_frames"])) != (
        960, 540, 480
    ):
        raise SystemExit(f"unexpected MP4 geometry/frame count: {probe}")
    if not 15.9 <= float(probe["duration"]) <= 16.1:
        raise SystemExit(f"unexpected MP4 duration: {probe['duration']}")
    print("Verified source provenance and fully decoded GIF/MP4 media.")


if __name__ == "__main__":
    main()
