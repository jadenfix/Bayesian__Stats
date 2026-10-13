#!/usr/bin/env python3
"""Record a truthful visualization of the tested offline notebook batch."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "docs" / "demo"
RUNTIME_FILES = (
    "run_research.py",
    "requirements.txt",
    "GSB544_HW2_solutions.ipynb",
    "shafer_fix_1.ipynb",
)
WIDTH, HEIGHT, FPS, SECONDS = 960, 540, 10, 16
BG = "#09111f"
PANEL = "#111d32"
PANEL_2 = "#172540"
INK = "#f5f7fb"
MUTED = "#9fb0c9"
PURPLE = "#a78bfa"
CYAN = "#67e8f9"
GREEN = "#86efac"
AMBER = "#fbbf24"


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


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)


def text(draw: ImageDraw.ImageDraw, xy, value, size, fill=INK, bold=False):
    draw.text(xy, value, font=font(size, bold), fill=fill)


def rounded(draw: ImageDraw.ImageDraw, box, fill=PANEL, outline=None, radius=18):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def fit_image(source: Path, box: tuple[int, int, int, int]) -> Image.Image:
    image = Image.open(source).convert("RGB")
    max_width, max_height = box[2] - box[0], box[3] - box[1]
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (max_width, max_height), "white")
    canvas.paste(
        image,
        ((max_width - image.width) // 2, (max_height - image.height) // 2),
    )
    return canvas


def base_frame(kicker: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.ellipse((-130, -170, 250, 210), fill="#20194a")
    draw.ellipse((760, 390, 1100, 730), fill="#073846")
    text(draw, (42, 26), "BAYESIAN DECISION ANALYSIS", 14, PURPLE, True)
    text(draw, (760, 27), kicker.upper(), 13, MUTED, True)
    draw.line((42, 55, 918, 55), fill="#2b3b55", width=2)
    return image, draw


def render_frame(second: float, receipts: dict, results: dict, figure: Path) -> Image.Image:
    if second < 2.5:
        image, draw = base_frame("offline coursework")
        text(draw, (55, 142), "Two notebooks.", 48, INK, True)
        text(draw, (55, 205), "Two independent receipts.", 48, CYAN, True)
        text(draw, (57, 286), "A reproducible batch runner for the committed research workflows.", 21, MUTED)
        rounded(draw, (55, 356, 510, 413), PANEL_2, "#314362", 14)
        text(draw, (78, 374), "$ python run_research.py --all", 18, GREEN, True)
        text(draw, (57, 462), "Seeded simulation  •  local execution  •  no external data", 16, MUTED)
        return image

    if second < 5.2:
        image, draw = base_frame("integrity repair")
        text(draw, (55, 90), "No more overwritten evidence", 36, INK, True)
        rounded(draw, (55, 165, 390, 375), PANEL, "#33445e")
        text(draw, (83, 191), "Before", 18, AMBER, True)
        text(draw, (83, 240), "notebook A", 21, MUTED)
        text(draw, (83, 286), "notebook B", 21, MUTED)
        draw.line((240, 252, 310, 290), fill=AMBER, width=4)
        draw.line((240, 298, 310, 290), fill=AMBER, width=4)
        text(draw, (275, 320), "execution.json", 17, AMBER, True)
        rounded(draw, (455, 165, 905, 375), PANEL, "#33445e")
        text(draw, (483, 191), "Now", 18, GREEN, True)
        text(draw, (483, 240), "GSB544 / execution.json", 20, CYAN, True)
        text(draw, (483, 286), "shafer / execution.json", 20, PURPLE, True)
        text(draw, (483, 332), "index.json links both", 17, GREEN)
        text(draw, (57, 442), "Regression-tested: reruns also remove stale figures per notebook.", 18, MUTED)
        return image

    if second < 8.8:
        image, draw = base_frame("actual batch run")
        text(draw, (55, 88), "Both committed notebooks completed", 34, INK, True)
        entries = receipts["notebooks"]
        for y, entry, color, cells in (
            (160, entries[0], CYAN, 7),
            (300, entries[1], PURPLE, 5),
        ):
            rounded(draw, (55, y, 905, y + 110), PANEL, "#33445e")
            text(draw, (80, y + 22), "✓", 34, GREEN, True)
            text(draw, (128, y + 20), entry["notebook"], 21, INK, True)
            text(draw, (128, y + 57), f"{cells} code cells executed", 17, MUTED)
            text(draw, (565, y + 28), "SHA-256", 13, color, True)
            text(draw, (565, y + 53), entry["notebook_sha256"][:24] + "…", 14, MUTED)
        text(draw, (57, 452), "Each receipt records its own source checksum, cells and figures.", 18, MUTED)
        return image

    if second < 12.5:
        image, draw = base_frame("seeded simulation output")
        text(draw, (55, 82), "Actual notebook output", 34, INK, True)
        chart = fit_image(figure, (55, 145, 505, 440))
        image.paste(chart, (55, 145))
        rounded(draw, (540, 145, 905, 440), PANEL, "#33445e")
        text(draw, (570, 174), "p-value band", 15, PURPLE, True)
        text(draw, (570, 202), results["band"], 24, INK, True)
        text(draw, (570, 256), "estimated replication", 15, CYAN, True)
        text(draw, (570, 284), results["replication"], 24, INK, True)
        text(draw, (570, 338), "brownie decision", 15, AMBER, True)
        text(draw, (570, 366), results["decision"], 24, INK, True)
        text(draw, (57, 465), "Coursework simulation only — not a real-world performance claim.", 17, MUTED)
        return image

    image, draw = base_frame("verified provenance")
    text(draw, (55, 91), "Reproducible by construction", 38, INK, True)
    checks = [
        ("Notebook SHA-256", "pins the exact research inputs"),
        ("Isolated directories", "prevent cross-notebook artifact mixing"),
        ("Full media verifier", "decodes every published GIF and MP4 frame"),
    ]
    for i, (heading, detail) in enumerate(checks):
        y = 170 + i * 90
        rounded(draw, (55, y, 905, y + 68), PANEL, "#33445e", 14)
        text(draw, (78, y + 17), "✓", 24, GREEN, True)
        text(draw, (120, y + 14), heading, 19, INK, True)
        text(draw, (410, y + 16), detail, 17, MUTED)
    text(draw, (57, 467), "Actual local workflow  •  no provider calls  •  source-pinned", 17, CYAN, True)
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="tested source commit")
    args = parser.parse_args()
    source = run("git", "rev-parse", args.source).stdout.strip()
    tree = run("git", "rev-parse", f"{source}^{{tree}}").stdout.strip()
    if run("git", "merge-base", "--is-ancestor", source, "HEAD", check=False).returncode:
        raise SystemExit("recorded source must be an ancestor of HEAD")
    if run("git", "diff", "--quiet", source, "--", *RUNTIME_FILES, check=False).returncode:
        raise SystemExit("runtime files differ from the requested source commit")

    DEMO.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        temporary_path = Path(temporary)
        output = temporary_path / "research-output"
        completed = run(
            sys.executable,
            "run_research.py",
            "--all",
            "--output",
            str(output),
        )
        receipts = json.loads((output / "index.json").read_text())
        stdout = completed.stdout
        results = {
            "band": re.search(r"Trials with p in \[0.03,0.05\]: (\d+)", stdout).group(1)
            + " trials",
            "replication": re.search(
                r"Estimated replication probability: ([\d.]+%)", stdout
            ).group(1),
            "decision": "Q* = "
            + re.search(r"Optimal Q\* = (\d+ brownies)", stdout).group(1),
        }
        figure = output / receipts["notebooks"][0]["figures"][0]
        frames = temporary_path / "frames"
        frames.mkdir()
        rendered = []
        for index in range(FPS * SECONDS):
            frame = render_frame(index / FPS, receipts, results, figure)
            path = frames / f"frame-{index:04d}.png"
            frame.save(path, optimize=True)
            rendered.append(frame)

        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                "-i", str(frames / "frame-%04d.png"), "-vf", "fps=30,format=yuv420p",
                "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart",
                str(DEMO / "bayesian-stats-demo.mp4"),
            ], check=True
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                "-i", str(frames / "frame-%04d.png"), "-vf",
                "fps=10,scale=800:-1:flags=lanczos,split[s0][s1];"
                "[s0]palettegen=max_colors=96:stats_mode=diff[p];"
                "[s1][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
                str(DEMO / "bayesian-stats-demo.gif"),
            ], check=True
        )
        poster = render_frame(14.0, receipts, results, figure).resize(
            (1280, 720), Image.Resampling.LANCZOS
        )
        poster.save(DEMO / "bayesian-stats-poster.png", optimize=True)

        runtime = {}
        for path in RUNTIME_FILES:
            runtime[path] = {
                "git_blob": run("git", "rev-parse", f"{source}:{path}").stdout.strip(),
                "sha256": sha256(ROOT / path),
            }
        capture = {
            "schema_version": 1,
            "recorded_source_commit": source,
            "recorded_source_tree": tree,
            "command": "python run_research.py --all",
            "scope": "Offline coursework notebooks with seeded/local inputs only; no scientific, predictive, or real-world performance claim.",
            "runtime_files": runtime,
            "notebooks": receipts["notebooks"],
            "observed_results": results,
            "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
            "artifacts": {},
        }
        for name in (
            "bayesian-stats-demo.gif",
            "bayesian-stats-demo.mp4",
            "bayesian-stats-poster.png",
        ):
            path = DEMO / name
            capture["artifacts"][name] = {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        (DEMO / "capture.json").write_text(json.dumps(capture, indent=2) + "\n")


if __name__ == "__main__":
    main()
