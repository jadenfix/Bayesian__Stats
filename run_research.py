"""Execute the committed notebook code without requiring a notebook server."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parent
NOTEBOOKS = ("GSB544_HW2_solutions.ipynb", "shafer_fix_1.ipynb")
SCOPE = (
    "Both committed decision-analysis notebooks run offline in full; no claim that "
    "the README illustrative PyMC examples or uncommitted case-study directories "
    "are implemented."
)


def notebook_slug(notebook: str) -> str:
    """Return a stable, filesystem-safe output directory for a notebook."""
    path = Path(notebook)
    if path.name != notebook or path.suffix != ".ipynb":
        raise ValueError(f"notebook must be a local .ipynb filename: {notebook!r}")
    return path.stem


def execute_notebook(notebook: str, output_root: Path, root: Path = ROOT) -> dict:
    """Run one notebook in an isolated namespace and write its own receipt."""
    import matplotlib.pyplot as plt
    import numpy as np

    notebook_path = root / notebook
    notebook_bytes = notebook_path.read_bytes()
    notebook_data = json.loads(notebook_bytes)
    output_dir = output_root / notebook_slug(notebook)
    output_dir.mkdir(parents=True, exist_ok=True)

    # A rerun must never retain figures from an earlier version of this notebook.
    for stale in output_dir.glob("figure-*.png"):
        stale.unlink()
    (output_dir / "execution.json").unlink(missing_ok=True)

    plt.close("all")
    np.random.seed(42)
    namespace = {
        "__name__": "__main__",
        "display": lambda *items: [print(item) for item in items],
    }
    started = time.perf_counter()
    executed = []

    for index, cell in enumerate(notebook_data["cells"]):
        if cell["cell_type"] != "code" or not "".join(cell["source"]).strip():
            continue
        source = "".join(cell["source"])
        if any(
            line.lstrip().startswith(("%", "!")) for line in source.splitlines()
        ):
            raise RuntimeError(
                "Notebook magic requires interactive Jupyter; this lane must "
                "contain ordinary Python"
            )
        print(f"Executing {notebook}: cell {index}", flush=True)
        exec(compile(source, f"{notebook}:cell{index}", "exec"), namespace)
        executed.append(index)

    figures = []
    for figure_number in plt.get_fignums():
        filename = f"figure-{figure_number}.png"
        plt.figure(figure_number).savefig(
            output_dir / filename, dpi=130, bbox_inches="tight"
        )
        figures.append(filename)
    plt.close("all")

    report = {
        "notebook": notebook,
        "notebook_sha256": hashlib.sha256(notebook_bytes).hexdigest(),
        "executed_cells": executed,
        "figures": figures,
        "elapsed_seconds": time.perf_counter() - started,
        "seed": 42,
        "sample_controls": {
            key: os.environ[key]
            for key in ("RESEARCH_N", "RESEARCH_MAX_ROWS")
            if key in os.environ
        },
        "scope": SCOPE,
    }
    if "results" in namespace and isinstance(namespace["results"], dict):
        report["model_results"] = namespace["results"]
    (output_dir / "execution.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n"
    )
    print(json.dumps(report, indent=2, default=str))
    return report


def run_many(notebooks: list[str], output_root: Path, root: Path = ROOT) -> dict:
    """Run notebooks and write an index that cannot conflate their artifacts."""
    output_root.mkdir(parents=True, exist_ok=True)
    # Never leave a previous successful batch index behind when a rerun fails.
    (output_root / "index.json").unlink(missing_ok=True)
    reports = [execute_notebook(name, output_root, root) for name in notebooks]
    index = {
        "notebooks": [
            {
                "notebook": report["notebook"],
                "notebook_sha256": report["notebook_sha256"],
                "receipt": f"{notebook_slug(report['notebook'])}/execution.json",
                "figures": [
                    f"{notebook_slug(report['notebook'])}/{figure}"
                    for figure in report["figures"]
                ],
            }
            for report in reports
        ],
        "scope": SCOPE,
    }
    (output_root / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("notebook", nargs="?", choices=NOTEBOOKS)
    selection.add_argument(
        "--all", action="store_true", help="run both committed notebooks"
    )
    parser.add_argument("--output", default="research-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    notebooks = list(NOTEBOOKS) if args.all else [args.notebook]
    output_root = args.output if args.output.is_absolute() else ROOT / args.output
    run_many(notebooks, output_root)


if __name__ == "__main__":
    main()
