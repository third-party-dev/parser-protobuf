#!/usr/bin/env python3

# apt-get install python3-libcst

import argparse
import libcst as cst
import sys
import tomllib
from pathlib import Path


class BlankLineRestorer(cst.CSTTransformer):
    # def leave_FunctionDef(
    #     self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    # ) -> cst.FunctionDef:
    #     return updated_node.with_changes(
    #         leading_lines=[cst.EmptyLine(), cst.EmptyLine()],
    #     )
    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Keep any existing lines that have content (comments etc)
        # Strip leading blank lines, then prepend two clean blank lines
        existing = updated_node.leading_lines
        non_blank = [
            line for line in existing
            if line.comment is not None
        ]
        return updated_node.with_changes(
            leading_lines=[
                cst.EmptyLine(indent=False),
                cst.EmptyLine(indent=False),
                *non_blank,
            ],
        )


def restore_blank_lines(source: str) -> str:
    tree = cst.parse_module(source)
    new_tree = tree.visit(BlankLineRestorer())
    return new_tree.code


def load_ruff_excludes(pyproject_path: Path) -> list[str]:
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    ruff = data.get("tool", {}).get("ruff", {})
    excludes = ruff.get("exclude", [])
    extend_excludes = ruff.get("extend-exclude", [])
    return excludes + extend_excludes


def find_pyproject() -> Path | None:
    for parent in [Path.cwd(), *Path.cwd().parents]:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None


def is_excluded(path: Path, excludes: list[str], root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    for pattern in excludes:
        pattern_path = Path(pattern)
        # Single directory name — match any part
        if len(pattern_path.parts) == 1:
            if any(part == pattern for part in rel.parts):
                return True
        else:
            # Multi-segment path — check if rel starts with it
            try:
                rel.relative_to(pattern_path)
                return True
            except ValueError:
                pass
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restore double blank lines between functions/methods after ruff format."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files or directories to process (default: .)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without writing any files",
    )
    args = parser.parse_args()

    pyproject = find_pyproject()
    excludes = []
    root = Path.cwd()

    if pyproject:
        print(f"Reading excludes from {pyproject}")
        excludes = load_ruff_excludes(pyproject)
        root = pyproject.parent
        if excludes:
            print(f"Excluding: {excludes}")
    else:
        print("No pyproject.toml found, no excludes applied")

    if args.dry_run:
        print("Dry run — no files will be written\n")

    processed = 0
    would_change = 0
    skipped = 0

    for base_path in [Path(p) for p in args.paths]:
        py_files = (
            [base_path] if base_path.is_file()
            else base_path.rglob("*.py")
        )
        for py_file in py_files:
            if is_excluded(py_file, excludes, root):
                #print(f"Skipping {py_file} (excluded)")
                skipped += 1
                continue
            try:
                source = py_file.read_text()
                result = restore_blank_lines(source)
                if result != source:
                    if args.dry_run:
                        print(f"Would update {py_file}")
                        would_change += 1
                    else:
                        py_file.write_text(result)
                        print(f"Updated {py_file}")
                processed += 1
            except Exception as e:
                print(f"Error processing {py_file}: {e}", file=sys.stderr)

    if args.dry_run:
        print(f"\nDry run: {would_change} files would be changed, {skipped} skipped ({processed} total scanned)")
    else:
        print(f"\nDone: {processed} files processed, {skipped} skipped")