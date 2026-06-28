#!/usr/bin/env python3
"""Validate skillreg release version consistency."""

from __future__ import annotations

import argparse
import sys

from versioning import check_versions, read_pyproject_version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-tag",
        action="store_true",
        help="Also require the current GitHub tag to equal v<pyproject version>.",
    )
    args = parser.parse_args()

    errors = check_versions(require_tag=args.require_tag)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"version ok: {read_pyproject_version()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
