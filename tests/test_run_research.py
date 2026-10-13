import json
import tempfile
import unittest
from pathlib import Path

from run_research import run_many


def notebook(*sources: str) -> dict:
    return {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [source],
            }
            for source in sources
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


class ResearchArtifactTests(unittest.TestCase):
    def test_batch_preserves_a_receipt_and_figures_for_each_notebook(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "first.ipynb").write_text(
                json.dumps(notebook("import matplotlib.pyplot as plt\nplt.plot([1, 2])"))
            )
            (root / "second.ipynb").write_text(
                json.dumps(notebook("answer = 6 * 7"))
            )

            index = run_many(
                ["first.ipynb", "second.ipynb"], root / "output", root
            )

            self.assertEqual(
                [entry["notebook"] for entry in index["notebooks"]],
                ["first.ipynb", "second.ipynb"],
            )
            first = json.loads(
                (root / "output/first/execution.json").read_text()
            )
            second = json.loads(
                (root / "output/second/execution.json").read_text()
            )
            self.assertEqual(first["figures"], ["figure-1.png"])
            self.assertEqual(second["figures"], [])
            self.assertTrue((root / "output/first/figure-1.png").is_file())
            self.assertEqual(
                json.loads((root / "output/index.json").read_text())["notebooks"],
                index["notebooks"],
            )

    def test_rerun_removes_stale_figures_from_that_notebook_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "study.ipynb"
            path.write_text(
                json.dumps(notebook("import matplotlib.pyplot as plt\nplt.plot([1, 2])"))
            )
            run_many(["study.ipynb"], root / "output", root)
            self.assertTrue((root / "output/study/figure-1.png").exists())

            path.write_text(json.dumps(notebook("answer = 6 * 7")))
            run_many(["study.ipynb"], root / "output", root)

            self.assertFalse((root / "output/study/figure-1.png").exists())
            receipt = json.loads(
                (root / "output/study/execution.json").read_text()
            )
            self.assertEqual(receipt["figures"], [])

    def test_failed_batch_does_not_leave_a_stale_success_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            (output / "index.json").write_text('{"stale": true}\n')
            (root / "broken.ipynb").write_text(
                json.dumps(notebook("raise RuntimeError('expected failure')"))
            )

            with self.assertRaisesRegex(RuntimeError, "expected failure"):
                run_many(["broken.ipynb"], output, root)

            self.assertFalse((output / "index.json").exists())


if __name__ == "__main__":
    unittest.main()
