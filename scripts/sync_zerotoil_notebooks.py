#!/usr/bin/env python3
"""Convert zero-toil/zerotoil Python modules to Jupyter notebooks.

Maps each .py file under zero-toil/zerotoil/ to a corresponding .ipynb
under jupyter-templates/Xstore/zerotoil/, e.g.:

    zero-toil/zerotoil/tsgs/csm_quorum_loss.py
    →  jupyter-templates/Xstore/zerotoil/tsgs/csm_quorum_loss.ipynb

Features:
    - Replaces ``from zerotoil.x.y import A, B`` with xportal.run_template calls
    - Preserves existing template_id GUIDs from target .ipynb files
    - Skips __init__.py and __pycache__

Usage:
    python zero-toil/scripts/sync_zerotoil_notebooks.py
"""

from __future__ import annotations

import ast
import json
import re
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ZEROTOIL_SRC = REPO_ROOT / "zero-toil" / "zerotoil"
NOTEBOOK_DST = REPO_ROOT / "jupyter-templates" / "Xstore" / "zerotoil"

NOTEBOOK_METADATA_BASE = {
    "language_info": {
        "codemirror_mode": {"name": "python", "version": 3},
        "file_extension": ".py",
        "mimetype": "text/x-python",
        "name": "python",
        "nbconvert_exporter": "python",
        "pygments_lexer": "ipython3",
        "version": "3.8",
    },
    "kernelspec": {
        "name": "python",
        "display_name": "Python (Pyodide)",
        "language": "python",
    },
}


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def read_existing_template_id(nb_path: Path) -> str | None:
    """Read template_id from an existing .ipynb file, if valid."""
    if not nb_path.exists():
        return None
    try:
        data = json.loads(nb_path.read_text("utf-8"))
        tid = data.get("metadata", {}).get("template_id", "")
        if isinstance(tid, str) and _UUID_RE.match(tid):
            return tid
    except (json.JSONDecodeError, OSError):
        pass
    return None


# ── Import transformation ───────────────────────────────────


def transform_zerotoil_imports(source: str) -> str:
    """Replace ``from zerotoil.* import ...`` with run_template calls.

    Also strips ``from __future__`` imports which break ``exec()`` in the
    notebook runtime (Python 3 / Pyodide — they are unnecessary).
    Uses the ``ast`` module for robust multi-line import handling.
    Non-zerotoil imports are left untouched.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        print("  WARNING: syntax error in source, skipping import transform")
        return source

    # Collect edits: (start_line, end_line, replacement_or_None)
    # replacement=None means delete the lines entirely.
    edits: list[tuple[int, int, str | None]] = []
    xportal_added = False

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if node.module == "__future__":
            # Strip — incompatible with exec() in notebook runtime
            edits.append((node.lineno, node.end_lineno, None))
        elif node.module.startswith("zerotoil"):
            names = [alias.name for alias in node.names]
            parts = node.module.split(".")
            nb_path = "/Xstore/zerotoil/" + "/".join(parts[1:]) + ".ipynb"

            lines: list[str] = []
            if not xportal_added:
                lines.append("import xportal")
                xportal_added = True
            lines.append(
                f"exports = await xportal.run_template('{nb_path}', outputs={names!r})"
            )
            for n in names:
                lines.append(f"{n} = exports['{n}']")
            edits.append((node.lineno, node.end_lineno, "\n".join(lines) + "\n"))

    if not edits:
        return source

    edits.sort(key=lambda t: t[0])

    source_lines = source.splitlines(keepends=True)
    result: list[str] = []
    prev_end = 0  # 0-based index of next unconsumed line

    for start_line, end_line, replacement in edits:
        result.extend(source_lines[prev_end : start_line - 1])
        if replacement is not None:
            result.append(replacement)
        prev_end = end_line  # end_line is 1-based, so index end_line is next line

    # Remaining lines after the last edit
    result.extend(source_lines[prev_end:])
    return "".join(result)


def detect_tsg_class_name(source: str) -> str | None:
    """Return the TSG class name when the module defines one, else None."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "TsgBase":
                return node.name
            if isinstance(base, ast.Attribute) and base.attr == "TsgBase":
                return node.name

    return None


# ── Notebook generation ─────────────────────────────────────


def make_code_cell(source_lines: list[str]) -> dict:
    """Build a Jupyter code cell with normalized metadata."""
    return {
        "cell_type": "code",
        "source": source_lines,
        "metadata": {},
        "execution_count": None,
        "outputs": [],
    }


def make_notebook(
    code: str, source_display: str, template_id: str, tsg_class_name: str | None
) -> dict:
    """Build a Jupyter notebook dict for a zerotoil module."""
    metadata = {**NOTEBOOK_METADATA_BASE, "template_id": template_id}

    md_cell = {
        "cell_type": "markdown",
        "source": [
            f"Auto-generated from `{source_display}`\n",
            "\n",
            "Do not edit manually — re-run `sync_zerotoil_notebooks.py` to refresh.\n",
        ],
        "metadata": {},
    }

    # Notebook source array: each line ends with \n except the last
    raw_lines = code.split("\n")
    nb_source: list[str] = []
    for i, line in enumerate(raw_lines):
        if i < len(raw_lines) - 1:
            nb_source.append(line + "\n")
        else:
            # Last segment — only add if non-empty
            if line:
                nb_source.append(line)
    # If the file ended with a trailing \n, the last split element is ""
    # which we already skip above.

    cells: list[dict] = []

    if tsg_class_name:
        cells.append(make_code_cell(["incident_id = None"]))

    cells.append(md_cell)
    cells.append(make_code_cell(nb_source))

    if tsg_class_name:
        cells.append(
            make_code_cell(
                [
                    "if incident_id:\n",
                    f"    tsg = {tsg_class_name}()\n",
                    "    await tsg.run_for_incident(str(incident_id))",
                ]
            )
        )

    return {
        "metadata": metadata,
        "nbformat": 4,
        "nbformat_minor": 4,
        "cells": cells,
    }


# ── Main ────────────────────────────────────────────────────


def main() -> None:
    if not ZEROTOIL_SRC.is_dir():
        print(f"ERROR: source not found: {ZEROTOIL_SRC}", file=sys.stderr)
        sys.exit(1)

    converted = 0

    for py_file in sorted(ZEROTOIL_SRC.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        if "__pycache__" in py_file.parts:
            continue

        rel = py_file.relative_to(ZEROTOIL_SRC)
        nb_rel = rel.with_suffix(".ipynb")
        nb_path = NOTEBOOK_DST / nb_rel

        tid = read_existing_template_id(nb_path) or str(uuid.uuid4())

        source = py_file.read_text("utf-8")
        transformed = transform_zerotoil_imports(source)
        tsg_class_name = detect_tsg_class_name(source)

        nb_rel_display = str(nb_rel).replace("\\", "/")
        source_display = "zero-toil/zerotoil/" + str(rel).replace("\\", "/")
        notebook = make_notebook(transformed, source_display, tid, tsg_class_name)

        nb_path.parent.mkdir(parents=True, exist_ok=True)
        nb_path.write_text(
            json.dumps(notebook, indent=2, ensure_ascii=False) + "\n", "utf-8"
        )

        print(f"  {source_display} -> jupyter-templates/Xstore/zerotoil/{nb_rel_display}")
        converted += 1

    print(f"\nConverted: {converted} files")


if __name__ == "__main__":
    main()
